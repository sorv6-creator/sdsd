from aiogram import Bot
from aiogram.types import LabeledPrice


async def send_invoice(bot: Bot, chat_id: int, subject):
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"{subject['emoji']} Курс: {subject['name']}",
        description=(
            subject["description"]
            or f"Доступ к полному курсу «{subject['name']}» для подготовки к ЕГЭ"
        )[:255],
        payload=f"subject_{subject['id']}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=subject["name"], amount=subject["price_stars"])],
        start_parameter=f"buy_{subject['id']}",
    )