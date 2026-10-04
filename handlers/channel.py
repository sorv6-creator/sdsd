from aiogram import Router, F, Bot
from aiogram.types import PreCheckoutQuery, Message, SuccessfulPayment
from aiogram.exceptions import TelegramBadRequest

from config import REFERRAL_PURCHASE_REWARD
from database import (
    add_purchase, get_subject, user_has_purchased,
    get_setting, get_user, add_balance,
)

router = Router()


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    channel = await get_setting("subscribe_channel_id", "@EGE_Market")
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest as e:
        print(f"[WARN] Проверка подписки: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Проверка подписки: {e}")
        return False


async def add_user_to_channel(bot: Bot, channel_id: str, user_id: int) -> bool:
    """
    Пытается автоматически добавить пользователя в канал.
    Работает через unban_chat_member: если юзер не в канале — он добавляется,
    если был забанен — разбанивается.
    Требует у бота прав «Блокировать участников» в канале.
    """
    try:
        await bot.unban_chat_member(
            chat_id=channel_id,
            user_id=user_id,
            only_if_banned=False,
        )
        return True
    except Exception as e:
        print(f"[WARN] Авто-добавление не удалось: {e}")
        return False


async def issue_access(bot: Bot, user_id: int, subject, method: str = "auto"):
    """
    Выдаёт доступ к курсу: пробует авто-добавить, при неудаче шлёт ссылку.
    Возвращает текст для отправки пользователю.
    """
    channel_id = subject["channel_id"]
    if not channel_id:
        return "✅ Оплата прошла! Но канал курса не настроен. Свяжитесь с админом."

    auto_ok = await add_user_to_channel(bot, channel_id, user_id)

    if auto_ok:
        try:
            await bot.send_message(
                user_id,
                f"✅ <b>Ты автоматически добавлен в канал курса!</b>\n\n"
                f"Курс: <b>{subject['emoji']} {subject['name']}</b>\n\n"
                f"Открой Telegram — канал появится в твоих чатах.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # В любом случае даём invite-ссылку на случай, если авто не сработало у клиента
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=channel_id, member_limit=1,
            name=f"Access_{user_id}",
        )
        link = invite.invite_link
    except Exception as e:
        link = f"https://t.me/c/{str(channel_id).replace('-100', '')}"
        print(f"[WARN] invite: {e}")

    template = await get_setting(
        "purchase_success_text",
        "🎉 Оплата прошла! Ссылка: {link}"
    )
    text = template.replace("{subject_name}", f"{subject['emoji']} {subject['name']}")
    text = text.replace("{link}", link)
    return text


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, bot: Bot):
    if not await is_subscribed(bot, query.from_user.id):
        await query.answer(ok=False, error_message="Сначала подпишитесь на канал!")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, bot: Bot):
    payment: SuccessfulPayment = message.successful_payment
    subject_id = int(payment.invoice_payload.split("_")[1])
    subject = await get_subject(subject_id)

    if not subject:
        await message.answer("⚠️ Ошибка: предмет не найден.")
        return

    await add_purchase(
        user_id=message.from_user.id,
        subject_id=subject_id,
        payment_id=payment.telegram_payment_charge_id,
        amount_stars=payment.total_amount,
        method="stars",
    )

    buyer = await get_user(message.from_user.id)
    if buyer and buyer["referrer_id"]:
        ref_id = buyer["referrer_id"]
        await add_balance(ref_id, REFERRAL_PURCHASE_REWARD,
                          from_user_id=message.from_user.id,
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

    text = await issue_access(bot, message.from_user.id, subject, "stars")
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("get_access:"))
async def reissue_access(call, bot: Bot):
    subject_id = int(call.data.split(":")[1])
    subject = await get_subject(subject_id)

    if not subject:
        await call.answer("Предмет не найден", show_alert=True)
        return
    if not await user_has_purchased(call.from_user.id, subject_id):
        await call.answer("У вас нет доступа к этому курсу", show_alert=True)
        return
    if not await is_subscribed(bot, call.from_user.id):
        await call.answer("⚠️ Подпишитесь на канал снова.", show_alert=True)
        return

    text = await issue_access(bot, call.from_user.id, subject, "reissue")
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()