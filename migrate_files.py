"""
migrate_files.py
Scans Files/ folder and migrates everything into Resources/ with proper structure.
- JPG photo bursts → compiled into a single PDF per exam set
- PDFs/PPTX/DOCX already in Files/ → copied directly if not already in Resources/
"""

import sys
import shutil
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("WARNING: Pillow not installed. JPG files cannot be compiled to PDF.")
    print("Run: pip install Pillow")

# ─── Mappings ─────────────────────────────────────────────────────────────────
SUBJECT_MAP = {
    "English":    "ENGL101",
    "Geography":  "GEOG101",
    "Logic":      "LOGI101",
    "Maths":      "MATH101",
    "Physics":    "PHYS101",
    "Psychology": "PSYC101",
}

# Folder-name → resource type key used in Resources/
TYPE_MAP = {
    "Exams":          "exams",
    "Exam":           "exams",
    "Module":         "modules",
    "Modules":        "modules",
    "WorkSheet":      "worksheets",
    "WorkSheets":     "worksheets",
    "Worksheet":      "worksheets",
    "Worksheets":     "worksheets",
    "ppt":            "slides",
    "PPT":            "slides",
    "Slides":         "slides",
    "Harley":         "modules",   # Logic Harley book → module
    "Serway":         "modules",   # Physics Serway book → module
    "Teachers_Guide": "handwritten",
}

BASE     = Path(".")
FILES    = BASE / "Files"
RESOURCES = BASE / "Resources"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def ensure(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path

def compile_jpg_to_pdf(jpg_files: list, out_pdf: Path):
    """Compile a sorted list of JPG paths into a single PDF."""
    if not PIL_AVAILABLE:
        print(f"  [SKIP] Cannot compile {out_pdf.name} — Pillow not installed")
        return False
    imgs = []
    for jpg in sorted(jpg_files):
        try:
            im = Image.open(jpg).convert("RGB")
            imgs.append(im)
        except Exception as e:
            print(f"  [WARN] Could not open {jpg.name}: {e}")
    if not imgs:
        return False
    imgs[0].save(out_pdf, save_all=True, append_images=imgs[1:])
    print(f"  [PDF] Created {out_pdf.name} ({len(imgs)} pages)")
    return True

def safe_copy(src: Path, dst: Path):
    """Copy src → dst only if dst doesn't already exist."""
    if dst.exists():
        print(f"  [SKIP] Already exists: {dst.relative_to(RESOURCES)}")
        return
    ensure(dst.parent)
    shutil.copy2(src, dst)
    print(f"  [COPY] {dst.relative_to(RESOURCES)}")

# ─── Exam-photo detection ─────────────────────────────────────────────────────
# Photos are named like: photo_2026-10-13_13-13-39.jpg
# We group consecutive bursts into a single PDF per subject/exam-type.

def group_photos(photo_files: list) -> list:
    """
    Given a list of Path objects for photo_*.jpg files,
    group them into contiguous time-based bursts separated by > 30-second gaps.
    Returns list of lists (each inner list is one PDF group).
    """
    from datetime import datetime

    def parse_dt(p: Path):
        # photo_YYYY-MM-DD_HH-MM-SS.jpg  or  photo_YYYY-MM-DD_HH-MM-SS (2).jpg
        name = p.stem.replace(" (2)", "").replace(" (3)", "")
        try:
            return datetime.strptime(name, "photo_%Y-%m-%d_%H-%M-%S")
        except Exception:
            return None

    dated = [(p, parse_dt(p)) for p in sorted(photo_files)]
    dated = [(p, dt) for p, dt in dated if dt is not None]
    undated = [p for p, dt in [(p, parse_dt(p)) for p in sorted(photo_files)] if dt is None]

    groups = []
    current = []
    prev_dt = None
    GAP_SECONDS = 120  # treat >2 min gap as new exam

    for p, dt in dated:
        if prev_dt is None or (dt - prev_dt).total_seconds() > GAP_SECONDS:
            if current:
                groups.append(current)
            current = [p]
        else:
            current.append(p)
        prev_dt = dt

    if current:
        groups.append(current)

    if undated:
        groups.append(undated)

    return groups

# ─── Main migration logic ─────────────────────────────────────────────────────

def migrate():
    print("=" * 60)
    print("  FILES -> RESOURCES Migration")
    print("=" * 60)

    for subj_dir in sorted(FILES.iterdir()):
        if not subj_dir.is_dir():
            continue
        course = SUBJECT_MAP.get(subj_dir.name)
        if not course:
            print(f"\n[UNKNOWN SUBJECT] {subj_dir.name} — skipping")
            continue

        print(f"\n{'-'*50}")
        print(f"  {subj_dir.name} -> {course}")
        print(f"{'-'*50}")

        for type_dir in sorted(subj_dir.iterdir()):
            if not type_dir.is_dir():
                continue

            res_type = TYPE_MAP.get(type_dir.name)
            if not res_type:
                print(f"  [UNKNOWN TYPE] {type_dir.name} — skipping")
                continue

            all_files = sorted(type_dir.iterdir())
            jpgs   = [f for f in all_files if f.suffix.lower() in (".jpg", ".jpeg")]
            others = [f for f in all_files if f.suffix.lower() not in (".jpg", ".jpeg")]

            # ── Non-photo files: copy directly ─────────────────────────────
            for f in others:
                if res_type == "exams":
                    # Put directly in exams/ — no year subfolder for direct PDFs
                    dst = RESOURCES / course / "exams" / f.name
                else:
                    dst = RESOURCES / course / res_type / f.name
                safe_copy(f, dst)

            # ── Photo files: group & compile into PDFs ─────────────────────
            if jpgs:
                groups = group_photos(jpgs)
                print(f"  [PHOTOS] {len(jpgs)} images -> {len(groups)} PDF group(s)")
                for idx, grp in enumerate(groups, 1):
                    set_label = f"Set {idx}" if len(groups) > 1 else ""
                    page_count = len(grp)
                    name_parts = [
                        subj_dir.name,
                        type_dir.name,
                    ]
                    if set_label:
                        name_parts.append(set_label)
                    name_parts.append(f"({page_count} Pages)")
                    pdf_name = " ".join(name_parts) + ".pdf"

                    if res_type == "exams":
                        dst_pdf = RESOURCES / course / "exams" / pdf_name
                    else:
                        dst_pdf = RESOURCES / course / res_type / pdf_name

                    if dst_pdf.exists():
                        print(f"  [SKIP] Already exists: {dst_pdf.name}")
                        continue

                    ensure(dst_pdf.parent)
                    compile_jpg_to_pdf(grp, dst_pdf)

    print("\n" + "=" * 60)
    print("  Migration complete!")
    print("=" * 60)

    # Summary
    print("\n=== Resources Summary ===")
    for course_dir in sorted(RESOURCES.iterdir()):
        if course_dir.is_dir():
            total = sum(1 for f in course_dir.rglob("*") if f.is_file())
            print(f"  {course_dir.name}: {total} files")


if __name__ == "__main__":
    migrate()
