from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS, REFERRAL_PURCHASE_REWARD
from database import (
    get_subject, get_setting, create_pending_payment,
    get_pending_payment, update_pending_status,
    add_purchase, add_balance, get_user, user_has_purchased,
    get_user_pending_payments,
)
from keyboards import (
    payment_details_kb, payment_review_kb, back_button, main_menu,
)
from handlers.channel import issue_access

router = Router()


class PaymentState(StatesGroup):
    waiting_screenshot = State()


@router.callback_query(F.data.startswith("pay_money:"))
async def show_payment_details(call: CallbackQuery):
    subject_id = int(call.data.split(":")[1])
    subject = await get_subject(subject_id)
    if not subject:
        await call.answer("Курс не найден", show_alert=True)
        return

    details = await get_setting("payment_details_text", "Реквизиты не заданы.")
    text = (
        f"<b>{subject['emoji']} {subject['name']}</b>\n"
        f"💰 К оплате: <b>{subject['price_rub']} ₽</b>\n\n"
        f"{details}"
    )
    try:
        await call.message.edit_text(text, reply_markup=payment_details_kb(subject_id))
    except Exception:
        await call.message.answer(text, reply_markup=payment_details_kb(subject_id))
    await call.answer()


@router.callback_query(F.data.startswith("paid:"))
async def ask_screenshot(call: CallbackQuery, state: FSMContext):
    subject_id = int(call.data.split(":")[1])
    subject = await get_subject(subject_id)
    if not subject:
        await call.answer("Курс не найден", show_alert=True)
        return

    if await user_has_purchased(call.from_user.id, subject_id):
        await call.answer("У вас уже есть доступ", show_alert=True)
        return

    await state.set_state(PaymentState.waiting_screenshot)
    await state.update_data(subject_id=subject_id)

    await call.message.answer(
        f"📸 <b>Отправь скриншот чека</b>\n\n"
        f"Курс: <b>{subject['emoji']} {subject['name']}</b>\n"
        f"Сумма: <b>{subject['price_rub']} ₽</b>\n\n"
        f"Пришли фото одним сообщением.\nОтменить — /cancel",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(PaymentState.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    subject_id = data["subject_id"]
    subject = await get_subject(subject_id)

    if not subject:
        await message.answer("⚠️ Ошибка. Попробуй снова.")
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    payment_id = await create_pending_payment(
        user_id=message.from_user.id,
        subject_id=subject_id,
        amount_rub=subject["price_rub"],
        method="money",
        screenshot_file_id=file_id,
    )

    sent_text = await get_setting(
        "payment_sent_text",
        "📸 Скриншот получен! Ожидай проверки."
    )
    await message.answer(sent_text, reply_markup=back_button("back_main"))

    user = message.from_user
    caption = (
        f"💳 <b>Новая заявка на оплату #{payment_id}</b>\n\n"
        f"👤 Покупатель: {user.full_name}\n"
        f"🔗 @{user.username or '—'}\n"
        f"🆔 <code>{user.id}</code>\n\n"
        f"📚 Курс: {subject['emoji']} {subject['name']}\n"
        f"💰 Сумма: <b>{subject['price_rub']} ₽</b>"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=payment_review_kb(payment_id),
            )
        except Exception as e:
            print(f"[WARN] Не удалось отправить админу {admin_id}: {e}")

    await state.clear()


@router.message(PaymentState.waiting_screenshot)
async def wrong_screenshot(message: Message):
    await message.answer("❌ Нужно отправить именно фото (скриншот чека).")


@router.message(F.text == "/cancel")
async def cancel_payment(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu())


# ============================================================
# АДМИН: ПОДТВЕРЖДЕНИЕ / ОТКЛОНЕНИЕ
# ============================================================

@router.callback_query(F.data.startswith("approve_payment:"))
async def approve_payment(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    pending = await get_pending_payment(payment_id)
    if not pending or pending["status"] != "pending":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    subject = await get_subject(pending["subject_id"])
    if not subject:
        await call.answer("Курс не найден", show_alert=True)
        return

    await add_purchase(
        user_id=pending["user_id"],
        subject_id=pending["subject_id"],
        payment_id=f"manual_{payment_id}",
        amount_rub=pending["amount_rub"],
        method="money",
    )
    await update_pending_status(payment_id, "approved")

    # Реферальное начисление
    buyer = await get_user(pending["user_id"])
    if buyer and buyer["referrer_id"]:
        ref_id = buyer["referrer_id"]
        await add_balance(ref_id, REFERRAL_PURCHASE_REWARD,
                          from_user_id=pending["user_id"],
                          reason="referral_purchase")
        try:
            await bot.send_message(
                ref_id,
                f"💰 <b>Твой реферал купил курс!</b>\n\n"
                f"Начислено: <b>+{REFERRAL_PURCHASE_REWARD} ₽</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # Выдача доступа
    access_text = await issue_access(bot, pending["user_id"], subject, "manual")
    try:
        await bot.send_message(pending["user_id"], access_text, parse_mode="HTML")
    except Exception as e:
        print(f"[WARN] Не смог отправить пользователю: {e}")

    # Обновляем сообщение админа
    try:
        await call.message.edit_caption(
            caption=f"{call.message.caption}\n\n✅ <b>ОДОБРЕНО</b>",
            parse_mode="HTML",
        )
    except Exception:
        try:
            await call.message.edit_text(
                f"{call.message.text}\n\n✅ <b>ОДОБРЕНО</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await call.answer("✅ Одобрено, доступ выдан")


@router.callback_query(F.data.startswith("reject_payment:"))
async def reject_payment(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    payment_id = int(call.data.split(":")[1])
    pending = await get_pending_payment(payment_id)
    if not pending or pending["status"] != "pending":
        await call.answer("Заявка уже обработана", show_alert=True)
        return

    subject = await get_subject(pending["subject_id"])
    await update_pending_status(payment_id, "rejected")

    template = await get_setting(
        "payment_rejected_text",
        "❌ Оплата отклонена. Курс: {subject_name}."
    )
    text = template.replace(
        "{subject_name}",
        f"{subject['emoji']} {subject['name']}" if subject else "—"
    ).replace("{reason}", "чек не подтверждён")

    try:
        await bot.send_message(pending["user_id"], text, parse_mode="HTML")
    except Exception as e:
        print(f"[WARN] Не смог отправить: {e}")

    try:
        await call.message.edit_caption(
            caption=f"{call.message.caption}\n\n❌ <b>ОТКЛОНЕНО</b>",
            parse_mode="HTML",
        )
    except Exception:
        try:
            await call.message.edit_text(
                f"{call.message.text}\n\n❌ <b>ОТКЛОНЕНО</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await call.answer("❌ Отклонено")


@router.callback_query(F.data == "my_pending")
async def my_pending(call: CallbackQuery):
    pendings = await get_user_pending_payments(call.from_user.id)
    if not pendings:
        await call.answer("У вас нет активных заявок", show_alert=True)
        return

    text = "⏳ <b>Мои заявки на оплату:</b>\n\n"
    for p in pendings:
        text += (
            f"• {p['emoji']} {p['subject_name']} — {p['amount_rub']} ₽\n"
            f"  <i>от {str(p['created_at'])[:16]}</i>\n"
        )
    text += "\nПосле проверки админом доступ придёт автоматически."

    await call.message.edit_text(text, reply_markup=back_button("profile"),
                                 parse_mode="HTML")
    await call.answer()