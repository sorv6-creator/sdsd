import aiosqlite

DB = "data.db"


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                agreed INTEGER DEFAULT 0,
                balance_rub INTEGER DEFAULT 0,
                referrer_id INTEGER,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price_stars INTEGER NOT NULL DEFAULT 1,
                price_rub INTEGER NOT NULL DEFAULT 100,
                photo_file_id TEXT,
                channel_id TEXT,
                description TEXT,
                emoji TEXT DEFAULT '📘',
                status TEXT DEFAULT 'available',
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 100
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER,
                payment_id TEXT,
                amount_stars INTEGER DEFAULT 0,
                amount_rub INTEGER DEFAULT 0,
                method TEXT DEFAULT 'stars',
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_id INTEGER,
                amount_rub INTEGER,
                method TEXT,
                screenshot_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user_id INTEGER,
                amount_rub INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        defaults = {
            "welcome_text": (
                "👋 <b>Привет!</b>\n\n"
                "Тут собраны актуальные курсы для подготовки к ЕГЭ <b>2025–2026</b>.\n\n"
                "💬 По любым вопросам пиши менеджеру: @mishaykazahpik\n\n"
                "Перед началом ознакомься с правилами 👇"
            ),
            "menu_text": (
                "🦉 <b>Главное меню</b>\n\n"
                "<i>Курсы для подготовки к ЕГЭ 2025–2026.</i>\n\n"
                "Выбери нужный раздел:"
            ),
            "subscribe_text": (
                "📢 <b>Обязательная подписка</b>\n\n"
                "Чтобы пользоваться ботом и получить доступ к курсам, "
                "подпишись на наш канал 👇\n\n"
                "После подписки нажми <b>«✅ Я подписался»</b>."
            ),
            "support_text": (
                "🛟 <b>Поддержка</b>\n\n"
                "Есть вопросы по оплате, доступу или курсам?\n"
                "Пиши менеджеру: @mishaykazahpik\n\n"
                "Отвечаем в течение 24 часов."
            ),
            "faq_text": (
                "💬 <b>Отзывы / FAQ</b>\n\n"
                "<b>❓ Как оплатить курс?</b>\n"
                "Три способа:\n"
                "• 💰 С баланса — моментально\n"
                "• ⭐ Telegram Stars — моментально\n"
                "• 💳 СБП/Карта — вручную, до 24 ч\n\n"
                "<b>❓ Когда откроется доступ?</b>\n"
                "При оплате балансом/Stars — сразу. "
                "При оплате деньгами — после проверки чека.\n\n"
                "<b>❓ Сколько стоит?</b>\n"
                "Каждый курс — от 1 ⭐ или от 100 ₽.\n\n"
                "<b>❓ Как работает реферальная программа?</b>\n"
                "За каждого друга — +10 ₽, за покупку друга — ещё +50 ₽."
            ),
            "promo_text": (
                "🎟 <b>Промокод</b>\n\n"
                "Введи промокод и получи скидку или бонус.\n\n"
                "Пока активных промокодов нет — следи за новостями в канале!"
            ),
            "referral_text": (
                "🤝 <b>Реферальная программа</b>\n\n"
                "<b>Как это работает:</b>\n"
                "• За каждого друга по твоей ссылке — <b>+10 ₽</b>\n"
                "• Если друг купит любой курс — ещё <b>+50 ₽</b>\n\n"
                "🔗 Твоя ссылка:\n<code>{ref_link}</code>\n\n"
                "👥 Приглашено: <b>{referrals_count}</b>\n"
                "💰 Заработано: <b>{total_earned} ₽</b>\n"
                "💎 Баланс: <b>{balance} ₽</b>\n\n"
                "<i>Для вывода напиши в поддержку.</i>"
            ),
            "purchase_success_text": (
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Курс «{subject_name}» открыт.\n\n"
                "🔗 Ваша персональная ссылка:\n{link}\n\n"
                "⚠️ Ссылка одноразовая — используйте сразу."
            ),
            "out_of_stock_text": "❌ <b>Курс временно недоступен</b>",
            "soon_text": "⏳ <b>Скоро в продаже</b>",

            "payment_details_text": (
                "💳 <b>Реквизиты для оплаты</b>\n\n"
                "<b>СБП по номеру телефона:</b>\n"
                "<code>+7 (900) 000-00-00</code>\n"
                "Банк: Т-Банк\n"
                "Получатель: Иван И.\n\n"
                "<b>Перевод на карту:</b>\n"
                "<code>2200 7000 0000 0000</code>\n\n"
                "⚠️ В комментарии укажи:\n"
                "<code>Оплата курса</code>\n\n"
                "После оплаты нажми <b>«✅ Я оплатил»</b> и отправь скриншот."
            ),
            "payment_choose_text": (
                "💳 <b>Выбери способ оплаты</b>\n\n"
                "• 💰 <b>Баланс</b> — моментально\n"
                "• ⭐ <b>Stars</b> — моментально\n"
                "• 💳 <b>СБП / Карта</b> — вручную, до 24 ч"
            ),
            "payment_sent_text": (
                "📸 <b>Скриншот получен!</b>\n\n"
                "Заявка отправлена администратору. "
                "Проверка до 24 часов.\n\n"
                "После подтверждения автоматически придёт ссылка."
            ),
            "payment_approved_text": (
                "✅ <b>Оплата подтверждена!</b>\n\n"
                "Курс «{subject_name}» открыт.\n\n"
                "🔗 Ссылка: {link}"
            ),
            "payment_rejected_text": (
                "❌ <b>Оплата отклонена</b>\n\n"
                "Курс: «{subject_name}»\nПричина: {reason}\n\n"
                "Если это ошибка — напиши в поддержку."
            ),

            "subscribe_channel_url": "https://t.me/EGE_Market",
            "subscribe_channel_id": "@EGE_Market",
            "support_contact": "@mishaykazahpik",
            "terms_url": "https://telegra.ph",
            "reviews_url": "https://t.me/EGE_Market",
            "reviews_faq_url": "https://t.me/EGE_Market",

            "welcome_photo": "",
            "menu_photo": "",
            "subscribe_photo": "",
            "support_photo": "",
            "faq_photo": "",
        }
        for k, v in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

        await db.commit()

    await _seed_subjects()


async def _seed_subjects():
    subjects = [
        ("Математика (профиль)", 1, 150, "📐", "Профильная математика: алгебра, геометрия, параметры, экономические задачи."),
        ("Русский язык", 1, 120, "📖", "Теория + практика: сочинение, тестовая часть, разбор заданий ФИПИ."),
        ("Физика", 1, 150, "🔬", "Механика, термодинамика, электродинамика, квантовая физика."),
        ("Химия", 1, 150, "🧪", "Органическая и неорганическая химия, задачи и реакции."),
        ("Биология", 1, 130, "🧬", "Ботаника, зоология, анатомия, генетика, эволюция, экология."),
        ("Информатика", 1, 150, "💻", "Программирование, алгоритмы, базы данных, задания 24–27."),
        ("История", 1, 130, "🏛", "Древняя Русь, Российская империя, СССР, современность."),
        ("Обществознание", 1, 120, "⚖️", "Человек и общество, экономика, социология, право."),
        ("Английский язык", 1, 140, "🇬🇧", "Аудирование, чтение, грамматика, письмо, устная часть."),
        ("География", 1, 120, "🌍", "Физическая и экономическая география, карты, статистика."),
        ("Литература", 1, 130, "📚", "Древнерусская литература, классика XIX–XX веков, анализ."),
        ("Немецкий язык", 1, 140, "🇩🇪", "Все разделы ЕГЭ по немецкому языку."),
        ("Французский язык", 1, 140, "🇫🇷", "Все разделы ЕГЭ по французскому языку."),
        ("Испанский язык", 1, 140, "🇪🇸", "Все разделы ЕГЭ по испанскому языку."),
        ("Китайский язык", 1, 140, "🇨🇳", "Иероглифика, грамматика, аудирование, чтение."),
    ]

    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM subjects") as cur:
            count = (await cur.fetchone())[0]
        if count > 0:
            return
        for i, (name, price_stars, price_rub, emoji, desc) in enumerate(subjects):
            await db.execute(
                "INSERT INTO subjects "
                "(name, price_stars, price_rub, channel_id, description, emoji, sort_order) "
                "VALUES (?,?,?,?,?,?,?)",
                (name, price_stars, price_rub, "@your_courses_channel", desc, emoji, (i + 1) * 10),
            )
        await db.commit()
        print(f"✅ Автозаполнение: {len(subjects)} предметов ЕГЭ.")


# ---------- USERS ----------

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)",
            (user_id, username, full_name),
        )
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def mark_user_agreed(user_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET agreed=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def user_agreed(user_id: int) -> bool:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT agreed FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def set_referrer(user_id: int, referrer_id: int) -> bool:
    if user_id == referrer_id:
        return False
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return False
        await db.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (referrer_id, user_id))
        await db.commit()
        return True


async def get_referrals_count(user_id: int) -> int:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,)) as cur:
            return (await cur.fetchone())[0]


async def get_user_purchases(user_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT p.*, s.name AS subject_name, s.emoji AS emoji
            FROM purchases p
            JOIN subjects s ON s.id = p.subject_id
            WHERE p.user_id=?
            ORDER BY p.purchased_at DESC
        """, (user_id,)) as cur:
            return await cur.fetchall()


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount_stars), 0), COALESCE(SUM(amount_rub), 0) "
            "FROM purchases WHERE user_id=?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return {
        "purchases": row[0] or 0,
        "spent_stars": row[1] or 0,
        "spent_rub": row[2] or 0,
    }


# ---------- BALANCE / REFERRALS ----------

async def add_balance(user_id: int, amount_rub: int, from_user_id: int = 0, reason: str = ""):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET balance_rub = balance_rub + ? WHERE user_id=?",
            (amount_rub, user_id),
        )
        await db.execute(
            "INSERT INTO referral_earnings (user_id, from_user_id, amount_rub, reason) "
            "VALUES (?,?,?,?)",
            (user_id, from_user_id, amount_rub, reason),
        )
        await db.commit()


async def deduct_balance(user_id: int, amount_rub: int) -> bool:
    """Списывает с баланса, если хватает. Возвращает True при успехе."""
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT balance_rub FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row or (row[0] or 0) < amount_rub:
            return False
        await db.execute(
            "UPDATE users SET balance_rub = balance_rub - ? WHERE user_id=?",
            (amount_rub, user_id),
        )
        await db.commit()
        return True


async def get_user_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT balance_rub FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return (row[0] if row else 0) or 0


async def get_referral_earned_total(user_id: int) -> int:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(amount_rub), 0) FROM referral_earnings WHERE user_id=?",
            (user_id,)
        ) as cur:
            return (await cur.fetchone())[0] or 0


async def get_referral_history(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM referral_earnings
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


# ---------- SUBJECTS ----------

async def get_subjects(only_active: bool = True):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM subjects"
        if only_active:
            q += " WHERE is_active=1"
        q += " ORDER BY sort_order, id"
        async with db.execute(q) as cur:
            return await cur.fetchall()


async def get_subject(subject_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)) as cur:
            return await cur.fetchone()


async def add_subject(name: str, price_stars: int, price_rub: int,
                      channel_id: str, description: str = "",
                      emoji: str = "📘", sort_order: int = 100):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO subjects "
            "(name, price_stars, price_rub, channel_id, description, emoji, sort_order) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, price_stars, price_rub, channel_id, description, emoji, sort_order),
        )
        await db.commit()


async def update_subject(subject_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [subject_id]
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE subjects SET {fields} WHERE id=?", values)
        await db.commit()


async def delete_subject(subject_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        await db.commit()


# ---------- PURCHASES ----------

async def add_purchase(user_id: int, subject_id: int, payment_id: str,
                       amount_stars: int = 0, amount_rub: int = 0,
                       method: str = "stars"):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO purchases "
            "(user_id, subject_id, payment_id, amount_stars, amount_rub, method) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, subject_id, payment_id, amount_stars, amount_rub, method),
        )
        await db.commit()


async def user_has_purchased(user_id: int, subject_id: int) -> bool:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT 1 FROM purchases WHERE user_id=? AND subject_id=?",
            (user_id, subject_id),
        ) as cur:
            return await cur.fetchone() is not None


# ---------- PENDING PAYMENTS ----------

async def create_pending_payment(user_id: int, subject_id: int,
                                  amount_rub: int, method: str,
                                  screenshot_file_id: str) -> int:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO pending_payments "
            "(user_id, subject_id, amount_rub, method, screenshot_file_id) "
            "VALUES (?,?,?,?,?)",
            (user_id, subject_id, amount_rub, method, screenshot_file_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_pending_payment(payment_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pending_payments WHERE id=?", (payment_id,)) as cur:
            return await cur.fetchone()


async def update_pending_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE pending_payments SET status=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, payment_id),
        )
        await db.commit()


async def get_pending_payments(status: str = "pending"):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT pp.*, s.name AS subject_name, s.emoji AS emoji
            FROM pending_payments pp
            JOIN subjects s ON s.id = pp.subject_id
            WHERE pp.status=?
            ORDER BY pp.created_at DESC
        """, (status,)) as cur:
            return await cur.fetchall()


async def get_user_pending_payments(user_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT pp.*, s.name AS subject_name, s.emoji AS emoji
            FROM pending_payments pp
            JOIN subjects s ON s.id = pp.subject_id
            WHERE pp.user_id=? AND pp.status='pending'
            ORDER BY pp.created_at DESC
        """, (user_id,)) as cur:
            return await cur.fetchall()


# ---------- STATS ----------

async def get_stats():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM purchases") as cur:
            purchases = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(amount_stars),0) FROM purchases") as cur:
            stars = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(amount_rub),0) FROM purchases") as cur:
            rub = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(amount_rub),0) FROM referral_earnings") as cur:
            ref_paid = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM pending_payments WHERE status='pending'") as cur:
            pending = (await cur.fetchone())[0]
    return {
        "users": users, "purchases": purchases, "stars": stars,
        "rub": rub, "ref_paid": ref_paid, "pending": pending,
    }


# ---------- SETTINGS ----------

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()