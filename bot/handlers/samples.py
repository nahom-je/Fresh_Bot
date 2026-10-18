from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import crud
from bot.db.models import User
from bot.keyboards.inline import materials_kb
from bot.utils.access import has_access
from bot.utils.telegram import safe_edit

router = Router()


from bot.keyboards.inline import open_menu_kb


@router.callback_query(F.data == "samples")
async def open_samples(cb: CallbackQuery) -> None:
    await cb.answer(
        "🔒 All materials require payment to unlock. Tap 'Pay to Unlock All Materials' on the main menu!",
        show_alert=True,
    )
