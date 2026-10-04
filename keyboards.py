from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


STATUS_EMOJI = {"available": "🟢", "out_of_stock": "🔴", "soon": "⏳"}


def welcome_kb(terms_url, reviews_url, support_contact):
    if support_contact.startswith("http"):
        support_url = support_contact
    elif support_contact.startswith("@"):
        support_url = f"https://t.me/{support_contact[1:]}"
    else:
        support_url = f"https://t.me/{support_contact}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Пользовательское соглашение", url=terms_url)],
        [InlineKeyboardButton(text="⭐ Отзывы", url=reviews_url)],
        [InlineKeyboardButton(text="🛟 Поддержка", url=support_url)],
        [InlineKeyboardButton(text="➡️ Продолжить", callback_data="agree_continue")],
    ])


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Курсы", callback_data="courses")],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="🎟 Промокод", callback_data="promo"),
        ],
        [
            InlineKeyboardButton(text="🛟 Инфо/Поддержка", callback_data="support"),
            InlineKeyboardButton(text="💬 Отзывы/FAQ", callback_data="faq"),
        ],
        [InlineKeyboardButton(text="🤝 Реферальная программа", callback_data="referral")],
    ])


def subscribe_kb(channel_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_url)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")],
    ])


def _short_name(name: str, limit: int = 13) -> str:
    """Убирает уточнения в скобках и сокращает длинные названия."""
    name = name.split("(")[0].strip()
    if len(name) > limit:
        name = name[:limit - 1] + "…"
    return name


def courses_menu(subjects):
    """Сетка 2 колонки: короткое название + цена."""
    rows = []
    current = []
    for s in subjects:
        status = s["status"] or "available"
        icon = STATUS_EMOJI.get(status, "🟢")
        short = _short_name(s["name"])

        if status == "available":
            price = f"{s['price_rub']}₽"
        elif status == "out_of_stock":
            price = "нет"
        else:
            price = "скоро"

        btn = InlineKeyboardButton(
            text=f"{icon} {s['emoji']} {short} · {price}",
            callback_data=f"subject:{s['id']}"
        )
        current.append(btn)
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subject_detail(subject_id, price_stars, price_rub, already_bought,
                   status="available"):
    if already_bought:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Получить доступ", callback_data=f"get_access:{subject_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="courses")],
        ])

    if status == "out_of_stock":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Нет в наличии", callback_data="not_available")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="courses")],
        ])
    if status == "soon":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Скоро", callback_data="not_available")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="courses")],
        ])

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Купить за {price_rub} ₽ / {price_stars} ⭐",
                              callback_data=f"buy:{subject_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="courses")],
    ])


def choose_payment_method(subject_id, price_stars, price_rub, balance: int = 0):
    buttons = []
    if balance >= price_rub:
        buttons.append([InlineKeyboardButton(
            text=f"💰 Оплатить с баланса ({price_rub} ₽)",
            callback_data=f"pay_balance:{subject_id}"
        )])
    buttons.append([InlineKeyboardButton(
        text=f"⭐ Оплатить {price_stars} Stars",
        callback_data=f"pay_stars:{subject_id}"
    )])
    buttons.append([InlineKeyboardButton(
        text=f"💳 Оплатить {price_rub} ₽ (СБП / Карта)",
        callback_data=f"pay_money:{subject_id}"
    )])
    buttons.append([InlineKeyboardButton(
        text="⬅️ Назад", callback_data=f"subject:{subject_id}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_details_kb(subject_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{subject_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"buy:{subject_id}")],
    ])


def payment_review_kb(payment_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_payment:{payment_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment:{payment_id}")],
    ])


def back_button(callback: str = "back_main", text: str = "⬅️ Назад"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback)]
    ])


def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Мои курсы", callback_data="my_purchases")],
        [InlineKeyboardButton(text="⏳ Мои заявки на оплату", callback_data="my_pending")],
        [InlineKeyboardButton(text="🤝 Пригласить друзей", callback_data="referral")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])


def referral_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 История начислений", callback_data="ref_history")],
        [InlineKeyboardButton(text="💬 Вывести баланс", callback_data="ref_withdraw")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])


# ---------- АДМИНКА ----------

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Предметы", callback_data="admin_subjects")],
        [InlineKeyboardButton(text="➕ Добавить предмет", callback_data="admin_add_subject")],
        [InlineKeyboardButton(text="💳 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="🖼 Фото экранов", callback_data="admin_photos")],
        [InlineKeyboardButton(text="📝 Все тексты", callback_data="admin_texts")],
        [InlineKeyboardButton(text="🔗 Ссылки", callback_data="admin_links")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⬅️ Закрыть", callback_data="back_main")],
    ])


def admin_payments_menu(pending_count: int = 0):
    badge = f" ({pending_count})" if pending_count else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📥 Заявки на проверку{badge}",
                              callback_data="admin_pending_list")],
        [InlineKeyboardButton(text="📝 Реквизиты оплаты",
                              callback_data="edit_text:payment_details_text")],
        [InlineKeyboardButton(text="💬 Текст выбора способа",
                              callback_data="edit_text:payment_choose_text")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])


def admin_photos_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Фото приветствия", callback_data="edit_photo:welcome_photo")],
        [InlineKeyboardButton(text="🏠 Фото меню", callback_data="edit_photo:menu_photo")],
        [InlineKeyboardButton(text="📢 Фото подписки", callback_data="edit_photo:subscribe_photo")],
        [InlineKeyboardButton(text="🛟 Фото поддержки", callback_data="edit_photo:support_photo")],
        [InlineKeyboardButton(text="💬 Фото FAQ", callback_data="edit_photo:faq_photo")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])


def admin_texts_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Приветствие", callback_data="edit_text:welcome_text")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="edit_text:menu_text")],
        [InlineKeyboardButton(text="📢 Подписка", callback_data="edit_text:subscribe_text")],
        [InlineKeyboardButton(text="🛟 Поддержка", callback_data="edit_text:support_text")],
        [InlineKeyboardButton(text="💬 FAQ", callback_data="edit_text:faq_text")],
        [InlineKeyboardButton(text="🎟 Промокод", callback_data="edit_text:promo_text")],
        [InlineKeyboardButton(text="🤝 Рефералы", callback_data="edit_text:referral_text")],
        [InlineKeyboardButton(text="🎉 После покупки Stars", callback_data="edit_text:purchase_success_text")],
        [InlineKeyboardButton(text="💳 Реквизиты оплаты", callback_data="edit_text:payment_details_text")],
        [InlineKeyboardButton(text="❌ Нет в наличии", callback_data="edit_text:out_of_stock_text")],
        [InlineKeyboardButton(text="⏳ Скоро", callback_data="edit_text:soon_text")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])


def admin_links_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Ссылка на канал", callback_data="edit_link:subscribe_channel_url")],
        [InlineKeyboardButton(text="🆔 ID канала (проверка)", callback_data="edit_link:subscribe_channel_id")],
        [InlineKeyboardButton(text="🛟 Контакт поддержки", callback_data="edit_link:support_contact")],
        [InlineKeyboardButton(text="📄 Оферта", callback_data="edit_link:terms_url")],
        [InlineKeyboardButton(text="⭐ Отзывы", callback_data="edit_link:reviews_url")],
        [InlineKeyboardButton(text="💬 FAQ-канал", callback_data="edit_link:reviews_faq_url")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
    ])


def admin_subjects_menu(subjects):
    buttons = []
    for s in subjects:
        status = s["status"] or "available"
        icon = STATUS_EMOJI.get(status, "🟢")
        active = "🟢" if s["is_active"] else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{active} {icon} {s['emoji']} {s['name']} — {s['price_rub']} ₽ / {s['price_stars']} ⭐",
            callback_data=f"admin_subject:{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_subject_edit(subject_id, is_active, status):
    toggle_active = "🔴 Скрыть полностью" if is_active else "🟢 Показать полностью"
    status_text = {
        "available": "🟢 В наличии → нажми для смены",
        "out_of_stock": "🔴 Нет в наличии → нажми для смены",
        "soon": "⏳ Скоро → нажми для смены",
    }.get(status, "🟢 В наличии")

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_name:{subject_id}")],
        [InlineKeyboardButton(text="⭐ Цена в Stars", callback_data=f"edit_price:{subject_id}")],
        [InlineKeyboardButton(text="💰 Цена в рублях", callback_data=f"edit_price_rub:{subject_id}")],
        [InlineKeyboardButton(text=status_text, callback_data=f"cycle_status:{subject_id}")],
        [InlineKeyboardButton(text="🖼 Фото курса", callback_data=f"edit_photo_subject:{subject_id}")],
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_desc:{subject_id}")],
        [InlineKeyboardButton(text="😀 Эмодзи", callback_data=f"edit_emoji:{subject_id}")],
        [InlineKeyboardButton(text="🔗 ID канала курса", callback_data=f"edit_channel:{subject_id}")],
        [InlineKeyboardButton(text="🔢 Порядок", callback_data=f"edit_order:{subject_id}")],
        [InlineKeyboardButton(text=toggle_active, callback_data=f"toggle_active:{subject_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_subject:{subject_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_subjects")],
    ])