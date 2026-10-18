from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import crud
from bot.db.models import User
from bot.keyboards.inline import exam_courses_kb, materials_kb
from bot.utils.access import has_access
from bot.utils.telegram import safe_edit

router = Router()


@router.callback_query(F.data == "exams")
async def exams_hub(cb: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    courses = await crud.get_course_dict(session)
    ai_enabled = (await crud.get_value(session, "ai_enabled") or "true") == "true"
    await safe_edit(
        cb.message,
        "📝 <b>Past Exams Hub</b>\n\nChoose a course to view its exams:",
        exam_courses_kb(courses, ai_enabled, has_access(db_user)),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("ex:c:"))
async def exam_list(cb: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    """Show all exams for the selected course directly."""
    if not has_access(db_user):
        return await cb.answer(
            "🔒 Past exams are locked.\n\nPay to unlock full access to all courses, modules, and past exams!",
            show_alert=True,
        )

    code = cb.data.split(":")[2]
    courses = await crud.get_course_dict(session)
    if code not in courses:
        return await cb.answer("Unknown course.", show_alert=True)

    items = await crud.list_all_exams(session, code)

    if items:
        file_word = "file" if len(items) == 1 else "files"
        text = (
            f"📝 <b>{courses[code]}</b> — Past Exams\n────────────────────────\n"
            f"<i>Contains {len(items)} {file_word}</i>\n\n"
            "Tap an exam below to receive it directly in chat."
        )
    else:
        text = (
            f"📝 <b>{courses[code]}</b> — Past Exams\n────────────────────────\n\n"
            "<i>No exams uploaded yet — check back soon!</i>"
        )

    await safe_edit(
        cb.message,
        text,
        materials_kb(items, has_access(db_user), back="exams"),
    )
    await cb.answer()
