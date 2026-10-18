import asyncio
from bot.db.session import session_factory
from bot.db.models import Material
from sqlalchemy import select

async def main():
    async with session_factory() as s:
        res = await s.execute(
            select(Material.course_code, Material.category, Material.exam_year, Material.title)
            .where(Material.category.in_(["exams_mid", "exams_final"]))
            .order_by(Material.course_code, Material.category)
        )
        rows = res.all()
        print(f"Total exam rows: {len(rows)}\n")
        for r in rows:
            print(f"  {r.course_code} | {r.category} | year={r.exam_year} | {r.title[:50]}")

asyncio.run(main())
