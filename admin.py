from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS
from database import (
    get_subjects, get_subject, update_subject, add_subject,
    delete_subject, get_stats, set_setting, get_setting,
    get_pending_payments,
)
from keyboards import (
    admin_menu, admin_subjects_menu, admin_subject_edit,
    admin_texts_menu, admin_links_menu, admin_photos_menu,
    admin_payments_menu, back_button,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminState(StatesGroup):
    edit_name = State()
    edit_price = State()
    edit_price_rub = State()
    edit_photo_subject = State()
    edit_desc = State()
    edit_emoji = State()
    edit_channel = State()
    edit_order = State()
    edit_text = State()
    edit_link = State()
    edit_photo = State()
    add_name = State()
    add_price = State()
    add_price_rub = State()
    add_channel = State()


STATUS_CYCLE = ["available", "out_of_stock", "soon"]


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer(
        "🔧 <b>Менеджер-меню</b>\n\nВыберите раздел:",
        reply_markup=admin_menu(), parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "🔧 <b>Менеджер-меню</b>\n\nВыберите раздел:",
        reply_markup=admin_menu(), parse_mode="HTML",
    )
    await call.answer()


# ============================================================
# ПЛАТЕЖИ
# ============================================================

@router.callback_query(F.data == "admin_payments")
async def admin_payments(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pendings = await get_pending_payments("pending")
    await call.message.edit_text(
        f"💳 <b>Платежи</b>\n\nАктивных заявок: <b>{len(pendings)}</b>",
        reply_markup=admin_payments_menu(len(pendings)),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "admin_pending_list")
async def admin_pending_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pendings = await get_pending_payments("pending")
    if not pendings:
        await call.message.edit_text(
            "📥 <b>Активных заявок нет</b>",
            reply_markup=back_button("admin_payments"),
            parse_mode="HTML",
        )
        await call.answer()
        return

    text = f"📥 <b>Заявки на проверку ({len(pendings)}):</b>\n\n"
    for p in pendings[:20]:
        text += (
            f"• #{p['id']} {p['emoji']} {p['subject_name']}\n"
            f"  <code>{p['user_id']}</code> — {p['amount_rub']} ₽\n"
        )
    text += "\n<i>Откройте заявку из уведомления, чтобы одобрить/отклонить.</i>"

    await call.message.edit_text(
        text, reply_markup=back_button("admin_payments"),
        parse_mode="HTML",
    )
    await call.answer()


# ============================================================
# ПРЕДМЕТЫ
# ============================================================

@router.callback_query(F.data == "admin_subjects")
async def admin_subjects(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    subjects = await get_subjects(only_active=False)
    if not subjects:
        await call.message.edit_text(
            "📚 Предметов пока нет.",
            reply_markup=back_button("admin_back"),
        )
        await call.answer()
        return
    await call.message.edit_text(
        "📚 <b>Предметы:</b>\n\nНажмите для редактирования:",
        reply_markup=admin_subjects_menu(subjects), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_subject:"))
async def admin_subject_view(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    s = await get_subject(sid)
    if not s:
        await call.answer("Не найден", show_alert=True)
        return

    status_human = {
        "available": "🟢 В наличии",
        "out_of_stock": "🔴 Нет в наличии",
        "soon": "⏳ Скоро",
    }.get(s["status"] or "available", "—")

    text = (
        f"<b>{s['emoji']} {s['name']}</b>\n\n"
        f"⭐ Цена Stars: <b>{s['price_stars']}</b>\n"
        f"💰 Цена руб: <b>{s['price_rub']} ₽</b>\n"
        f"📦 Статус: {status_human}\n"
        f"📝 Описание: {s['description'] or '—'}\n"
        f"🔗 Канал: <code>{s['channel_id'] or '—'}</code>\n"
        f"🖼 Фото: {'есть' if s['photo_file_id'] else 'нет'}\n"
        f"🔢 Порядок: {s['sort_order']}\n"
        f"👁 Активен: {'🟢' if s['is_active'] else '🔴'}"
    )

    kb = admin_subject_edit(sid, bool(s["is_active"]), s["status"] or "available")

    if s["photo_file_id"]:
        try:
            await call.message.delete()
            await call.message.answer_photo(
                photo=s["photo_file_id"], caption=text,
                parse_mode="HTML", reply_markup=kb,
            )
            await call.answer()
            return
        except Exception:
            pass

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


async def _ask(call, state, new_state, sid, prompt):
    await state.set_state(new_state)
    await state.update_data(subject_id=sid)
    await call.message.answer(prompt)
    await call.answer()


@router.callback_query(F.data.startswith("edit_name:"))
async def edit_name_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_name, sid, "✏️ Введите новое название:")


@router.message(AdminState.edit_name)
async def edit_name_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_subject(data["subject_id"], name=message.text.strip())
    await state.clear()
    await message.answer("✅ Название обновлено.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("edit_price:"))
async def edit_price_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_price, sid, "⭐ Введите цену в Stars:")


@router.message(AdminState.edit_price)
async def edit_price_finish(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Нужно целое число:")
        return
    data = await state.get_data()
    await update_subject(data["subject_id"], price_stars=int(message.text.strip()))
    await state.clear()
    await message.answer("✅ Цена (Stars) обновлена.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("edit_price_rub:"))
async def edit_price_rub_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_price_rub, sid, "💰 Введите цену в рублях:")


@router.message(AdminState.edit_price_rub)
async def edit_price_rub_finish(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Нужно целое число:")
        return
    data = await state.get_data()
    await update_subject(data["subject_id"], price_rub=int(message.text.strip()))
    await state.clear()
    await message.answer("✅ Цена (руб) обновлена.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("cycle_status:"))
async def cycle_status(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    s = await get_subject(sid)
    current = s["status"] or "available"
    idx = STATUS_CYCLE.index(current) if current in STATUS_CYCLE else 0
    new_status = STATUS_CYCLE[(idx + 1) % len(STATUS_CYCLE)]
    await update_subject(sid, status=new_status)
    await call.answer(f"Статус → {new_status}")
    await admin_subject_view(call)


@router.callback_query(F.data.startswith("edit_photo_subject:"))
async def edit_photo_subject_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_photo_subject, sid,
               "🖼 Отправьте новое фото курса (или '-' чтобы удалить):")


@router.message(AdminState.edit_photo_subject, F.photo)
async def edit_photo_subject_finish(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    await update_subject(data["subject_id"], photo_file_id=file_id)
    await state.clear()
    await message.answer("✅ Фото курса обновлено.", reply_markup=admin_menu())


@router.message(AdminState.edit_photo_subject, F.text == "-")
async def edit_photo_subject_remove(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_subject(data["subject_id"], photo_file_id="")
    await state.clear()
    await message.answer("✅ Фото курса удалено.", reply_markup=admin_menu())


@router.message(AdminState.edit_photo_subject)
async def edit_photo_subject_wrong(message: Message):
    await message.answer("❌ Отправьте фото или '-'.")


@router.callback_query(F.data.startswith("edit_desc:"))
async def edit_desc_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_desc, sid,
               "📝 Введите новое описание ('-' чтобы очистить):")


@router.message(AdminState.edit_desc)
async def edit_desc_finish(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "-": text = ""
    data = await state.get_data()
    await update_subject(data["subject_id"], description=text)
    await state.clear()
    await message.answer("✅ Описание обновлено.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("edit_emoji:"))
async def edit_emoji_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_emoji, sid, "😀 Отправьте эмодзи:")


@router.message(AdminState.edit_emoji)
async def edit_emoji_finish(message: Message, state: FSMContext):
    emoji = message.text.strip()[:4]
    data = await state.get_data()
    await update_subject(data["subject_id"], emoji=emoji)
    await state.clear()
    await message.answer("✅ Эмодзи обновлён.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("edit_channel:"))
async def edit_channel_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_channel, sid,
               "🔗 Введите ID канала курса (-100... или @username):")


@router.message(AdminState.edit_channel)
async def edit_channel_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_subject(data["subject_id"], channel_id=message.text.strip())
    await state.clear()
    await message.answer("✅ Канал обновлён.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("edit_order:"))
async def edit_order_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await _ask(call, state, AdminState.edit_order, sid, "🔢 Введите число (меньше = выше):")


@router.message(AdminState.edit_order)
async def edit_order_finish(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Нужно целое число:")
        return
    data = await state.get_data()
    await update_subject(data["subject_id"], sort_order=int(message.text.strip()))
    await state.clear()
    await message.answer("✅ Порядок обновлён.", reply_markup=admin_menu())


@router.callback_query(F.data.startswith("toggle_active:"))
async def toggle_active(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    s = await get_subject(sid)
    await update_subject(sid, is_active=0 if s["is_active"] else 1)
    await call.answer("Статус изменён")
    await admin_subject_view(call)


@router.callback_query(F.data.startswith("delete_subject:"))
async def delete_subject_cb(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split(":")[1])
    await delete_subject(sid)
    await call.answer("Удалён", show_alert=True)
    await admin_subjects(call)


@router.callback_query(F.data == "admin_add_subject")
async def add_subject_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(AdminState.add_name)
    await call.message.answer("📝 Введите название предмета:")
    await call.answer()


@router.message(AdminState.add_name)
async def add_subject_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminState.add_price)
    await message.answer("⭐ Введите цену в Stars (целое число):")


@router.message(AdminState.add_price)
async def add_subject_price(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Нужно целое число:")
        return
    await state.update_data(price_stars=int(message.text.strip()))
    await state.set_state(AdminState.add_price_rub)
    await message.answer("💰 Введите цену в рублях:")


@router.message(AdminState.add_price_rub)
async def add_subject_price_rub(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Нужно целое число:")
        return
    await state.update_data(price_rub=int(message.text.strip()))
    await state.set_state(AdminState.add_channel)
    await message.answer("🔗 Введите ID канала курса (-100... или @username):")


@router.message(AdminState.add_channel)
async def add_subject_channel(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_subject(
        name=data["name"],
        price_stars=data["price_stars"],
        price_rub=data["price_rub"],
        channel_id=message.text.strip(),
        description="Описание скоро появится...", emoji="📘",
    )
    await state.clear()
    await message.answer("✅ Предмет добавлен!", reply_markup=admin_menu())


# ============================================================
# ФОТО ЭКРАНОВ
# ============================================================

@router.callback_query(F.data == "admin_photos")
async def admin_photos(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "🖼 <b>Фото экранов</b>",
        reply_markup=admin_photos_menu(), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit_photo:"))
async def edit_photo_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    key = call.data.split(":", 1)[1]
    await state.set_state(AdminState.edit_photo)
    await state.update_data(key=key)
    await call.message.answer(
        f"🖼 Отправьте фото для <code>{key}</code>.\nУдалить — <code>-</code>",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AdminState.edit_photo, F.photo)
async def edit_photo_finish(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    data = await state.get_data()
    await set_setting(data["key"], file_id)
    await state.clear()
    await message.answer("✅ Фото обновлено.", reply_markup=admin_menu())


@router.message(AdminState.edit_photo, F.text == "-")
async def edit_photo_remove(message: Message, state: FSMContext):
    data = await state.get_data()
    await set_setting(data["key"], "")
    await state.clear()
    await message.answer("✅ Фото удалено.", reply_markup=admin_menu())


@router.message(AdminState.edit_photo)
async def edit_photo_wrong(message: Message):
    await message.answer("❌ Отправьте фото или '-'.")


# ============================================================
# ТЕКСТЫ
# ============================================================

@router.callback_query(F.data == "admin_texts")
async def admin_texts(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "📝 <b>Все тексты бота</b>",
        reply_markup=admin_texts_menu(), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit_text:"))
async def edit_text_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    key = call.data.split(":", 1)[1]
    current = await get_setting(key, "")
    await state.set_state(AdminState.edit_text)
    await state.update_data(key=key)
    await call.message.answer(
        f"📝 Текущий <code>{key}</code>:\n\n"
        f"<blockquote>{current[:300]}</blockquote>\n\n"
        f"Отправьте новый текст. HTML поддерживается.",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AdminState.edit_text)
async def edit_text_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await set_setting(data["key"], message.html_text)
    await state.clear()
    await message.answer("✅ Текст обновлён.", reply_markup=admin_menu())


# ============================================================
# ССЫЛКИ
# ============================================================

@router.callback_query(F.data == "admin_links")
async def admin_links(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.message.edit_text(
        "🔗 <b>Ссылки и контакты</b>",
        reply_markup=admin_links_menu(), parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit_link:"))
async def edit_link_start(call, state: FSMContext):
    if not is_admin(call.from_user.id): return
    key = call.data.split(":", 1)[1]
    current = await get_setting(key, "")
    await state.set_state(AdminState.edit_link)
    await state.update_data(key=key)
    await call.message.answer(
        f"🔗 Текущее <code>{key}</code>:\n<code>{current}</code>\n\nОтправьте новое:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AdminState.edit_link)
async def edit_link_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    await set_setting(data["key"], message.text.strip())
    await state.clear()
    await message.answer("✅ Ссылка обновлена.", reply_markup=admin_menu())


# ============================================================
# СТАТИСТИКА
# ============================================================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    st = await get_stats()
    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{st['users']}</b>\n"
        f"🛒 Покупок: <b>{st['purchases']}</b>\n"
        f"⭐ Через Stars: <b>{st['stars']}</b>\n"
        f"💰 Через деньги: <b>{st['rub']} ₽</b>\n"
        f"⏳ Заявок на проверке: <b>{st['pending']}</b>\n"
        f"💸 Выплачено рефералам: <b>{st['ref_paid']} ₽</b>",
        parse_mode="HTML",
        reply_markup=back_button("admin_back"),
    )
    await call.answer()