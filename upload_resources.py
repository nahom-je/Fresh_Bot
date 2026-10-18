"""
Automated Resource Ingestion Script for Freshman Bot
=====================================================
Recursively scans the `Resources/` folder, uploads materials to the private
Telegram storage channel, and registers them in the database (Supabase/PostgreSQL).

Usage:
    python upload_resources.py              # Ingest all files
    python upload_resources.py --dry-run    # Preview detected files without uploading
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

# Fix Windows console UTF-8 encoding for emojis
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import FSInputFile
from sqlalchemy import select

from bot.config import settings
from bot.db import crud
from bot.db.models import Course, Material
from bot.db.session import engine, init_db, session_factory

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("uploader")

RESOURCES_DIR = Path(__file__).resolve().parent / "Resources"

# Supported file extensions
VALID_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".txt", ".zip", ".rar",
    ".jpg", ".jpeg", ".png", ".mp4"
}

CATEGORY_MAP = {
    # canonical names (new structure)
    "module":        "module",
    "ppt":           "ppt",
    "teachersguide": "TeachersGuide",
    "worksheet":     "worksheet",
    # legacy aliases
    "modules":       "module",
    "slides":        "ppt",
    "handwritten":   "TeachersGuide",
    "worksheets":    "worksheet",
    "notes":         "TeachersGuide",
    "tutorials":     "worksheet",
    "books":         "book",
    "book":          "book",
    "textbook":      "book",
    "textbooks":     "book",
}

YEAR_PATTERN = re.compile(r"\b(201[0-9]|202[0-9])\b")


def parse_file_metadata(file_path: Path) -> dict | None:
    """
    Analyzes the relative path of a file inside Resources/ to deduce its:
      - course_code
      - category
      - exam_year (if exam)
      - title
      - is_sample flag
    """
    if file_path.suffix.lower() not in VALID_EXTENSIONS:
        return None

    # Ignore instruction and hidden files
    if file_path.name.lower() in ("how_to_use.txt", "readme.txt", "readme.md", ".gitkeep") or file_path.name.startswith("."):
        return None

    # Get path relative to Resources/
    try:
        rel_parts = file_path.relative_to(RESOURCES_DIR).parts
    except ValueError:
        return None

    if not rel_parts:
        return None

    from urllib.parse import unquote
    title = unquote(file_path.stem.replace("_", " ").strip())

    # Case 1: Global Samples folder: Resources/samples/...
    if rel_parts[0].lower() == "samples":
        course = "sample"
        if len(rel_parts) > 2:
            course = rel_parts[1].upper()
        return {
            "course_code": course,
            "category": "sample",
            "exam_year": None,
            "title": title,
            "is_sample": True,
            "file_path": file_path,
        }

    # First folder must be course code (e.g. MATH101)
    course_code = rel_parts[0].upper()

    # Case 2: In-course sample: Resources/MATH101/samples/...
    if len(rel_parts) >= 2 and rel_parts[1].lower() in ("sample", "samples"):
        return {
            "course_code": course_code,
            "category": "sample",
            "exam_year": None,
            "title": title,
            "is_sample": True,
            "file_path": file_path,
        }

    # Case 3: Exams: Resources/MATH101/exams/...
    if len(rel_parts) >= 2 and rel_parts[1].lower() in ("exam", "exams", "past_exams", "past exams"):
        exam_type = "exams_mid"
        exam_year = None

        # Look in path parts for 'mid', 'final', and year
        for part in rel_parts[2:]:
            lower = part.lower()
            if "final" in lower:
                exam_type = "exams_final"
            elif "mid" in lower:
                exam_type = "exams_mid"

            match = YEAR_PATTERN.search(part)
            if match:
                exam_year = int(match.group(1))

        # Also search in filename if not found in folder
        if not exam_year:
            match = YEAR_PATTERN.search(file_path.name)
            if match:
                exam_year = int(match.group(1))

        # Search filename for mid/final hint (but only as fallback)
        fname_lower = file_path.name.lower()
        if exam_type == "exams_mid" and "final" in fname_lower and "mid" not in fname_lower:
            exam_type = "exams_final"

        return {
            "course_code": course_code,
            "category": exam_type,
            "exam_year": exam_year,
            "title": title,
            "is_sample": False,
            "file_path": file_path,
        }

    # Case 4: Standard categories (module, ppt, TeachersGuide, worksheet)
    if len(rel_parts) >= 2:
        folder_category = rel_parts[1].lower()
        matched_category = CATEGORY_MAP.get(folder_category, "module")
        return {
            "course_code": course_code,
            "category": matched_category,
            "exam_year": None,
            "title": title,
            "is_sample": False,
            "file_path": file_path,
        }

    # Fallback if placed directly inside Resources/MATH101/file.pdf
    return {
        "course_code": course_code,
        "category": "module",
        "exam_year": None,
        "title": title,
        "is_sample": False,
        "file_path": file_path,
    }


async def is_already_uploaded(session, meta: dict) -> bool:
    """Checks if a matching material already exists in the database."""
    stmt = select(Material).where(
        Material.course_code == meta["course_code"],
        Material.category == meta["category"],
        Material.title == meta["title"],
        Material.is_sample == meta["is_sample"],
    )
    if meta["exam_year"] is not None:
        stmt = stmt.where(Material.exam_year == meta["exam_year"])

    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def ensure_course_exists(session, course_code: str) -> None:
    """Ensures the course exists in the database courses table."""
    if course_code == "sample":
        return
    course = await crud.get_course(session, course_code)
    if not course:
        name = settings.courses_dict.get(course_code, f"{course_code} Course")
        await crud.add_course(session, course_code, name)
        await session.commit()
        print(f"   ✨ Registered new course in DB: [{course_code}] {name}")


async def main():
    parser = argparse.ArgumentParser(description="Upload resources to Telegram storage & Supabase DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview scanned files without uploading")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 Freshman Bot — Automated Resource Ingestion")
    print(f"📂 Scanning Directory: {RESOURCES_DIR}")
    if args.dry_run:
        print("🔍 DRY RUN MODE: No files will be uploaded or inserted into DB.")
    print("=" * 70)

    if not RESOURCES_DIR.exists():
        print(f"❌ Error: Resources directory '{RESOURCES_DIR}' does not exist.")
        return

    # Find all files
    all_files = [p for p in RESOURCES_DIR.rglob("*") if p.is_file()]
    items = []
    for f in all_files:
        meta = parse_file_metadata(f)
        if meta:
            items.append(meta)

    if not items:
        print("⚠️ No valid files found in Resources/ directory.")
        print("Drop some PDF, PPTX, or DOCX files into Resources/ and try again!")
        return

    print(f"📦 Found {len(items)} eligible academic resource files.\n")

    if args.dry_run:
        print("--- PREVIEW OF DETECTED FILES ---")
        for i, meta in enumerate(items, 1):
            year_info = f" ({meta['exam_year']})" if meta["exam_year"] else ""
            sample_tag = " [FREE SAMPLE]" if meta["is_sample"] else ""
            print(f"[{i:02d}] Course: {meta['course_code']:<9} | Cat: {meta['category']}{year_info:<8} | Title: '{meta['title']}'{sample_tag}")
            print(f"     Path: {meta['file_path'].relative_to(RESOURCES_DIR)}")
        print("\n✅ Dry run complete. Run without --dry-run to upload to Telegram and Supabase.")
        return

    # Initialize Bot & DB
    await init_db()
    bot = Bot(token=settings.bot_token)

    uploaded_count = 0
    skipped_count = 0
    error_count = 0

    async with session_factory() as session:
        for idx, meta in enumerate(items, 1):
            prefix = f"[{idx}/{len(items)}]"

            # Check duplication
            if await is_already_uploaded(session, meta):
                print(f"⏩ {prefix} SKIP (Already in DB): {meta['course_code']} • {meta['category']} • {meta['title']}")
                skipped_count += 1
                continue

            # Skip files that exceed Telegram's 50MB bot API limit
            file_size_mb = meta["file_path"].stat().st_size / (1024 * 1024)
            if file_size_mb > 49:
                print(f"⚠️  {prefix} SKIP (File too large {file_size_mb:.1f}MB > 49MB): {meta['course_code']} • {meta['title']}")
                skipped_count += 1
                continue

            print(f"📤 {prefix} Uploading: {meta['course_code']} • {meta['category']} • '{meta['title']}'...")

            # Ensure course exists in database
            await ensure_course_exists(session, meta["course_code"])

            # Upload to Telegram Storage Channel
            try:
                input_file = FSInputFile(path=str(meta["file_path"]), filename=meta["file_path"].name)
                caption = f"{meta['course_code']} • {meta['category']} • {meta['title']}"

                # Handle flood wait protection
                sent_msg = None
                for attempt in range(3):
                    try:
                        sent_msg = await bot.send_document(
                            chat_id=settings.storage_channel_id,
                            document=input_file,
                            caption=caption[:1024],
                        )
                        break
                    except TelegramRetryAfter as tra:
                        print(f"   ⏳ Telegram rate limit. Sleeping {tra.retry_after}s...")
                        await asyncio.sleep(tra.retry_after + 1)

                if not sent_msg:
                    print(f"   ❌ Failed to send document after retries.")
                    error_count += 1
                    continue

                file_id = sent_msg.document.file_id if sent_msg.document else None

                # Insert into DB
                await crud.add_material(
                    session,
                    course_code=meta["course_code"],
                    category=meta["category"],
                    title=meta["title"],
                    channel_message_id=sent_msg.message_id,
                    file_id=file_id,
                    exam_year=meta["exam_year"],
                    is_sample=meta["is_sample"],
                )
                await session.commit()

                print(f"   ✅ Saved to DB! (Telegram Msg ID: {sent_msg.message_id})")
                uploaded_count += 1

                # Polite delay to respect Telegram API
                await asyncio.sleep(0.6)

            except TelegramAPIError as e:
                print(f"   ❌ Telegram Error: {e}")
                error_count += 1
            except Exception as ex:
                print(f"   ❌ Database / File Error: {ex}")
                error_count += 1

    await bot.session.close()
    await engine.dispose()

    print("\n" + "=" * 70)
    print("🎉 INGESTION SUMMARY:")
    print(f"   ✅ Successfully Uploaded & Saved: {uploaded_count}")
    print(f"   ⏩ Skipped (Already existed):    {skipped_count}")
    if error_count:
        print(f"   ❌ Errors encountered:          {error_count}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Ingestion canceled by user.")
        sys.exit(0)
