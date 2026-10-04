import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery,
    BotCommand, BotCommandScopeDefault, BotCommandScopeChat,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import (
    BOT_TOKEN, ADMIN_IDS,
    TERMS_URL, REVIEWS_URL, REVIEWS_FAQ_URL,
    REFERRAL_JOIN_REWARD,
)
from database import (
    init_db, add_user, get_subjects, get_subject,
    user_has_purchased, get_user, get_user_purchases,
    get_user_stats, get_setting, mark_user_agreed, user_agreed,
    set_referrer, get_referrals_count, get_user_balance,
    get_referral_earned_total, add_balance, get_referral_history,
    add_purchase, deduct_balance,
)
from keyboards import (
    main_menu, courses_menu, subject_detail,
    back_button, subscribe_kb, welcome_kb,
    profile_kb, referral_kb, choose_payment_method,
)
from payments import send_invoice

from handlers.channel import router as channel_router, is_subscribed, issue_access
from handlers.manual_payment import router as manual_payment_router
from admin import router as admin_router

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(manual_payment_router)
dp.include_router(channel_router)
dp.include_router(admin_router)


# ============================================================
# КОМАНДЫ
# ============================================================

async def set_bot_commands():
    user_commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="courses", description="📚 Курсы"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="support", description="🛟 Поддержка"),
        BotCommand(command="cancel", description="❌ Отменить действие"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command="admin", description="🔧 Админ-панель"),
    ]
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            print(f"[WARN] {admin_id}: {e}")


# ============================================================
# УНИВЕРСАЛЬНЫЙ ПОКАЗ
# ============================================================

async def show_screen(source, text: str, kb, photo: str = ""):
    if isinstance(source, CallbackQuery):
        chat_id = source.message.chat.id
        try:
            await source.message.delete()
        except Exception:
            pass
        if photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, reply_markup=kb)
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
    else:
        if photo:
            await source.answer_photo(photo=photo, caption=text, reply_markup=kb)
        else:
            await source.answer(text, reply_markup=kb)


# ============================================================
# /start
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name,
    )

    if command.args and command.args.startswith("ref_"):
        try:
            ref_id = int(command.args[4:])
            if ref_id != message.from_user.id:
                ok = await set_referrer(message.from_user.id, ref_id)
                if ok:
                    await add_balance(ref_id, REFERRAL_JOIN_REWARD,
                                      from_user_id=message.from_user.id,
                                      reason="referral_join")
                    try:
                        await bot.send_message(
                            ref_id,
                            f"🎉 <b>Новый реферал!</b>\n\n"
                            f"Начислено: <b>+{REFERRAL_JOIN_REWARD} ₽</b>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        except (ValueError, IndexError):
            pass

    if await user_agreed(message.from_user.id):
        await _send_main_menu(message)
        return

    welcome = await get_setting("welcome_text", "👋 <b>Привет!</b>")
    terms = await get_setting("terms_url", TERMS_URL)
    reviews = await get_setting("reviews_url", REVIEWS_URL)
    support = await get_setting("support_contact", "@mishaykazahpik")
    welcome_photo = await get_setting("welcome_photo", "")

    name = message.from_user.first_name or ""
    text = welcome.replace("Привет!", f"Привет, <b>{name}</b>!") if name else welcome

    kb = welcome_kb(terms, reviews, support)

    if welcome_photo:
        await message.answer_photo(photo=welcome_photo, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "agree_continue")
async def agree_continue(call: CallbackQuery):
    await mark_user_agreed(call.from_user.id)

    if not await is_subscribed(bot, call.from_user.id):
        await _show_subscribe_screen(call)
        return

    await _send_main_menu(call, delete_old=True)
    await call.answer()


# ============================================================
# ПОДПИСКА
# ============================================================

async def _show_subscribe_screen(source):
    subscribe_text = await get_setting("subscribe_text", "📢 Подпишитесь!")
    channel_url = await get_setting("subscribe_channel_url", "https://t.me/EGE_Market")
    subscribe_photo = await get_setting("subscribe_photo", "")
    kb = subscribe_kb(channel_url)
    await show_screen(source, subscribe_text, kb, subscribe_photo)


@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    if await is_subscribed(bot, call.from_user.id):
        await call.answer("✅ Подписка подтверждена!", show_alert=True)
        await _send_main_menu(call, delete_old=True)
    else:
        await call.answer("❌ Вы ещё не подписаны.", show_alert=True)


# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

async def _send_main_menu(source, delete_old: bool = False):
    menu_text = await get_setting("menu_text", "🦉 <b>Главное меню</b>")
    menu_photo = await get_setting("menu_photo", "")

    if delete_old or isinstance(source, CallbackQuery):
        await show_screen(source, menu_text, main_menu(), menu_photo)
    else:
        if menu_photo:
            await source.answer_photo(photo=menu_photo, caption=menu_text, reply_markup=main_menu())
        else:
            await source.answer(menu_text, reply_markup=main_menu())


@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    await _send_main_menu(call, delete_old=True)
    await call.answer()


# ============================================================
# КУРСЫ
# ============================================================

@dp.message(Command("courses"))
async def cmd_courses(message: Message):
    if not await is_subscribed(bot, message.from_user.id):
        await _show_subscribe_screen(message)
        return
    subjects = await get_subjects()
    if not subjects:
        await message.answer("Курсы пока не добавлены.")
        return
    await message.answer("📚 <b>Выберите предмет:</b>", reply_markup=courses_menu(subjects))


@dp.callback_query(F.data == "courses")
async def show_courses(call: CallbackQuery):
    if not await is_subscribed(bot, call.from_user.id):
        await _show_subscribe_screen(call)
        await call.answer()
        return
    subjects = await get_subjects()
    if not subjects:
        await call.answer("Курсы пока не добавлены", show_alert=True)
        return
    await show_screen(call, "📚 <b>Выберите предмет:</b>", courses_menu(subjects))
    await call.answer()


@dp.callback_query(F.data.startswith("subject:"))
async def show_subject(call: CallbackQuery):
    if not await is_subscribed(bot, call.from_user.id):
        await _show_subscribe_screen(call)
        await call.answer()
        return

    sid = int(call.data.split(":")[1])
    subject = await get_subject(sid)
    if not subject or not subject["is_active"]:
        await call.answer("Предмет недоступен", show_alert=True)
        return

    status = subject["status"] or "available"
    bought = await user_has_purchased(call.from_user.id, sid)

    status_human = {
        "available": "🟢 В наличии",
        "out_of_stock": "🔴 Нет в наличии",
        "soon": "⏳ Скоро в продаже",
    }.get(status, "")

    text = (
        f"<b>{subject['emoji']} {subject['name']}</b>\n\n"
        f"{subject['description'] or 'Описание скоро появится.'}\n\n"
        f"📦 Статус: {status_human}\n"
    )
    if status == "available":
        text += f"💰 Цена: <b>{subject['price_rub']} ₽</b> или <b>{subject['price_stars']} ⭐</b>"

    kb = subject_detail(sid, subject["price_stars"], subject["price_rub"],
                        bought, status)
    await show_screen(call, text, kb, subject["photo_file_id"] or "")
    await call.answer()


@dp.callback_query(F.data == "not_available")
async def not_available(call: CallbackQuery):
    await call.answer("Курс временно недоступен", show_alert=True)


# ============================================================
# ВЫБОР СПОСОБА ОПЛАТЫ
# ============================================================

@dp.callback_query(F.data.startswith("buy:"))
async def buy_subject(call: CallbackQuery):
    if not await is_subscribed(bot, call.from_user.id):
        await call.answer("Сначала подпишись на канал!", show_alert=True)
        return

    sid = int(call.data.split(":")[1])
    subject = await get_subject(sid)
    if not subject or not subject["is_active"]:
        await call.answer("Предмет недоступен", show_alert=True)
        return
    if (subject["status"] or "available") != "available":
        await call.answer("Курс недоступен для покупки", show_alert=True)
        return
    if await user_has_purchased(call.from_user.id, sid):
        await call.answer("У вас уже есть доступ к этому курсу", show_alert=True)
        return

    balance = await get_user_balance(call.from_user.id)
    choose_text = await get_setting("payment_choose_text", "💳 Выбери способ оплаты:")

    text = f"<b>{subject['emoji']} {subject['name']}</b>\n\n{choose_text}"
    if balance > 0:
        text += f"\n\n💰 Твой баланс: <b>{balance} ₽</b>"

    kb = choose_payment_method(sid, subject["price_stars"], subject["price_rub"], balance)
    await show_screen(call, text, kb)
    await call.answer()


@dp.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(call: CallbackQuery):
    if not await is_subscribed(bot, call.from_user.id):
        await call.answer("Сначала подпишись!", show_alert=True)
        return

    sid = int(call.data.split(":")[1])
    subject = await get_subject(sid)
    if not subject:
        await call.answer("Курс не найден", show_alert=True)
        return
    if await user_has_purchased(call.from_user.id, sid):
        await call.answer("Уже куплено", show_alert=True)
        return

    await send_invoice(bot, call.from_user.id, subject)
    await call.answer()


# ============================================================
# ОПЛАТА С БАЛАНСА
# ============================================================

@dp.callback_query(F.data.startswith("pay_balance:"))
async def pay_balance(call: CallbackQuery):
    if not await is_subscribed(bot, call.from_user.id):
        await call.answer("Сначала подпишись!", show_alert=True)
        return

    sid = int(call.data.split(":")[1])
    subject = await get_subject(sid)
    if not subject:
        await call.answer("Курс не найден", show_alert=True)
        return
    if await user_has_purchased(call.from_user.id, sid):
        await call.answer("У вас уже есть доступ", show_alert=True)
        return

    price = subject["price_rub"]
    balance = await get_user_balance(call.from_user.id)
    if balance < price:
        await call.answer(
            f"Недостаточно средств.\nНужно: {price} ₽\nУ тебя: {balance} ₽",
            show_alert=True,
        )
        return

    # Списываем баланс
    ok = await deduct_balance(call.from_user.id, price)
    if not ok:
        await call.answer("Не удалось списать. Попробуй позже.", show_alert=True)
        return

    # Записываем покупку
    await add_purchase(
        user_id=call.from_user.id,
        subject_id=sid,
        payment_id=f"balance_{call.from_user.id}_{sid}",
        amount_rub=price,
        method="balance",
    )

    # Начисление рефереру
    buyer = await get_user(call.from_user.id)
    if buyer and buyer["referrer_id"]:
        from config import REFERRAL_PURCHASE_REWARD
        ref_id = buyer["referrer_id"]
        await add_balance(ref_id, REFERRAL_PURCHASE_REWARD,
                          from_user_id=call.from_user.id,
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

    # Выдаём доступ
    access_text = await issue_access(bot, call.from_user.id, subject, "balance")
    await call.message.answer(access_text, parse_mode="HTML")
    await call.answer("✅ Оплата с баланса прошла!")


# ============================================================
# ПРОФИЛЬ
# ============================================================

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    await _send_profile(message)


@dp.callback_query(F.data == "profile")
async def show_profile(call: CallbackQuery):
    await _send_profile(call)
    await call.answer()


async def _send_profile(source):
    user = source.from_user
    user_row = await get_user(user.id)
    purchases = await get_user_purchases(user.id)
    stats = await get_user_stats(user.id)
    balance = await get_user_balance(user.id)
    ref_count = await get_referrals_count(user.id)

    reg_date = "—"
    if user_row and user_row["registered_at"]:
        reg_date = str(user_row["registered_at"])[:10]

    text = (
        f"👤 <b>Профиль</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📛 Имя: {user.full_name}\n"
        f"🔗 Username: @{user.username or 'не указан'}\n"
        f"📅 Регистрация: {reg_date}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>Баланс:</b> <b>{balance} ₽</b>\n"
        f"🤝 <b>Приглашено:</b> <b>{ref_count}</b>\n"
        f"🛒 <b>Куплено курсов:</b> <b>{stats['purchases']}</b>\n"
        f"⭐ <b>Потрачено Stars:</b> <b>{stats['spent_stars']}</b>\n"
        f"💰 <b>Потрачено ₽:</b> <b>{stats['spent_rub']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if purchases:
        text += "📚 <b>Последние курсы:</b>\n"
        for p in purchases[:5]:
            text += f"  • {p['emoji']} {p['subject_name']}\n"
    else:
        text += "📚 Пока нет покупок."

    await show_screen(source, text, profile_kb())


@dp.callback_query(F.data == "my_purchases")
async def my_purchases(call: CallbackQuery):
    purchases = await get_user_purchases(call.from_user.id)
    if not purchases:
        await call.answer("У вас пока нет покупок", show_alert=True)
        return
    text = "📚 <b>Мои курсы:</b>\n\n"
    for p in purchases:
        method_icon = {"stars": "⭐", "money": "💳", "balance": "💰"}.get(p["method"], "🛒")
        amount = f"{p['amount_stars']} ⭐" if p["method"] == "stars" else f"{p['amount_rub']} ₽"
        text += f"• {p['emoji']} {p['subject_name']} — {amount} {method_icon}\n"
    await show_screen(call, text, back_button("profile"))
    await call.answer()


# ============================================================
# РЕФЕРАЛЬНАЯ
# ============================================================

@dp.callback_query(F.data == "referral")
async def show_referral(call: CallbackQuery):
    template = await get_setting("referral_text", "🤝 Реферальная программа")
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{call.from_user.id}"

    ref_count = await get_referrals_count(call.from_user.id)
    earned = await get_referral_earned_total(call.from_user.id)
    balance = await get_user_balance(call.from_user.id)

    text = (template
            .replace("{ref_link}", ref_link)
            .replace("{referrals_count}", str(ref_count))
            .replace("{total_earned}", str(earned))
            .replace("{balance}", str(balance)))

    await show_screen(call, text, referral_kb())
    await call.answer()


@dp.callback_query(F.data == "ref_history")
async def ref_history(call: CallbackQuery):
    history = await get_referral_history(call.from_user.id, limit=15)
    if not history:
        await call.answer("История пуста", show_alert=True)
        return

    reasons = {
        "referral_join": "👥 Новый реферал",
        "referral_purchase": "🛒 Покупка реферала",
    }
    text = "📊 <b>История начислений:</b>\n\n"
    for h in history:
        date = str(h["created_at"])[:16]
        reason = reasons.get(h["reason"], h["reason"])
        text += f"• {reason} — <b>+{h['amount_rub']} ₽</b>\n  <i>{date}</i>\n"

    await show_screen(call, text, back_button("referral"))
    await call.answer()


@dp.callback_query(F.data == "ref_withdraw")
async def ref_withdraw(call: CallbackQuery):
    balance = await get_user_balance(call.from_user.id)
    if balance < 100:
        await call.answer(
            f"Минимум для вывода — 100 ₽.\nУ вас: {balance} ₽",
            show_alert=True,
        )
        return
    contact = await get_setting("support_contact", "@mishaykazahpik")
    if contact.startswith("@"):
        url = f"https://t.me/{contact[1:]}"
    else:
        url = f"https://t.me/{contact}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="referral")],
    ])
    text = (
        f"💸 <b>Вывод баланса</b>\n\n"
        f"Ваш баланс: <b>{balance} ₽</b>\n\n"
        f"Напишите в поддержку с реквизитами — переведём в течение 24 часов."
    )
    await show_screen(call, text, kb)
    await call.answer()


# ============================================================
# ПРОМО / ПОДДЕРЖКА / FAQ
# ============================================================

@dp.callback_query(F.data == "promo")
async def show_promo(call: CallbackQuery):
    promo_text = await get_setting("promo_text", "🎟 Промокод")
    await show_screen(call, promo_text, back_button("back_main"))
    await call.answer()


@dp.message(Command("support"))
async def cmd_support(message: Message):
    await _send_support(message)


@dp.callback_query(F.data == "support")
async def show_support(call: CallbackQuery):
    await _send_support(call)
    await call.answer()


async def _send_support(source):
    support_text = await get_setting("support_text", "🛟 Поддержка")
    support_photo = await get_setting("support_photo", "")
    contact = await get_setting("support_contact", "@mishaykazahpik")

    if contact.startswith("http"):
        contact_url = contact
    elif contact.startswith("@"):
        contact_url = f"https://t.me/{contact[1:]}"
    else:
        contact_url = f"https://t.me/{contact}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать в поддержку", url=contact_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])
    await show_screen(source, support_text, kb, support_photo)


@dp.callback_query(F.data == "faq")
async def show_faq(call: CallbackQuery):
    faq_text = await get_setting("faq_text", "💬 FAQ")
    faq_photo = await get_setting("faq_photo", "")
    reviews_url = await get_setting("reviews_url", REVIEWS_FAQ_URL)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Читать отзывы", url=reviews_url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])
    await show_screen(call, faq_text, kb, faq_photo)
    await call.answer()


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    await init_db()
    await set_bot_commands()
    print("🤖 Бот запущен!")
    print("📋 Команды установлены.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())