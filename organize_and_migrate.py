"""
Smart Resource Organizer & Compiler for Freshman Bot
=====================================================
Reads raw files from `Files/`:
1. Normalizes courses to official codes (MATH101, PHYS101, ENGL101, GEOG101, LOGI101, PSYC101).
2. Categorizes materials into modules, slides, worksheets, and handwritten notes.
3. Automatically compiles scattered exam photo bursts into clean multi-page PDF booklets using Pillow.
4. Populates high-value teaser files into `Resources/samples/` for free-tier users.
"""

import os
import re
import shutil
import sys
from pathlib import Path
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "Files"
RESOURCES_DIR = BASE_DIR / "Resources"

COURSE_MAP = {
    "Maths": "MATH101",
    "Physics": "PHYS101",
    "English": "ENGL101",
    "Geography": "GEOG101",
    "Logic": "LOGI101",
    "Psychology": "PSYC101",
}

def clean_title(filename: str) -> str:
    name = Path(filename).stem
    name = name.replace("_", " ").replace("%20", " ").replace("%28", "(").replace("%29", ")")
    name = re.sub(r"\s+", " ", name).strip()
    return name

def images_to_pdf(image_paths: list[Path], output_pdf: Path):
    if not image_paths:
        return
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    images = []
    for p in image_paths:
        try:
            im = Image.open(p)
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            images.append(im)
        except Exception as e:
            print(f"   ⚠️ Could not load image {p.name}: {e}")

    if not images:
        return

    first_image = images[0]
    rest_images = images[1:]
    first_image.save(output_pdf, "PDF", resolution=100.0, save_all=True, append_images=rest_images)
    print(f"   📄 Compiled {len(images)} pages -> {output_pdf.relative_to(RESOURCES_DIR)}")

def organize():
    print("=" * 70)
    print("🚀 Starting Automatic File Organization & PDF Compilation")
    print(f"Source: {FILES_DIR}")
    print(f"Target: {RESOURCES_DIR}")
    print("=" * 70)

    total_copied = 0
    total_compiled_exams = 0

    for subject_dir, course_code in COURSE_MAP.items():
        src_subject = FILES_DIR / subject_dir
        if not src_subject.exists():
            continue

        print(f"\n📂 Processing {subject_dir} -> [{course_code}]...")

        for sub in src_subject.iterdir():
            if not sub.is_dir():
                continue

            sub_lower = sub.name.lower()

            # --- Modules & Textbooks ---
            if sub_lower in ("module", "modules", "serway", "harley"):
                dest_dir = RESOURCES_DIR / course_code / "modules"
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in sub.iterdir():
                    if f.is_file():
                        dest_file = dest_dir / f.name
                        shutil.copy2(f, dest_file)
                        print(f"   📘 Module: {f.name}")
                        total_copied += 1

            # --- Teacher Guides / Notes ---
            elif sub_lower in ("teachers_guide", "teacher_guide"):
                dest_dir = RESOURCES_DIR / course_code / "handwritten"
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in sub.iterdir():
                    if f.is_file():
                        dest_file = dest_dir / f.name
                        shutil.copy2(f, dest_file)
                        print(f"   ✍️ Teacher Note: {f.name}")
                        total_copied += 1

            # --- Slides / PPTs ---
            elif sub_lower in ("ppt", "slides"):
                dest_dir = RESOURCES_DIR / course_code / "slides"
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in sub.iterdir():
                    if f.is_file():
                        dest_file = dest_dir / f.name
                        shutil.copy2(f, dest_file)
                        print(f"   📊 Slide: {f.name}")
                        total_copied += 1

            # --- Worksheets ---
            elif sub_lower in ("worksheet", "worksheets"):
                dest_dir = RESOURCES_DIR / course_code / "worksheets"
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in sub.iterdir():
                    if f.is_file():
                        dest_file = dest_dir / f.name
                        shutil.copy2(f, dest_file)
                        print(f"   🎯 Worksheet: {f.name}")
                        total_copied += 1

            # --- Exams ---
            elif sub_lower == "exams":
                exam_files = list(sub.iterdir())
                
                # 1. Handle Standalone PDFs
                for f in exam_files:
                    if f.is_file() and f.suffix.lower() == ".pdf":
                        name_lower = f.name.lower()
                        exam_type = "final" if "final" in name_lower else "mid"
                        
                        year_match = re.search(r"\b(201[0-9]|202[0-9])\b", f.name)
                        year = year_match.group(1) if year_match else "2016"
                        
                        dest_dir = RESOURCES_DIR / course_code / "exams" / exam_type / year
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest_file = dest_dir / f.name
                        shutil.copy2(f, dest_file)
                        print(f"   📝 Exam PDF ({exam_type.upper()} {year}): {f.name}")
                        total_copied += 1

                # 2. Handle Photo Bursts
                img_files = sorted([f for f in exam_files if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")])
                if img_files:
                    # Cluster photos by timestamp minute (photo_YYYY-MM-DD_HH-MM)
                    clusters = {}
                    for img in img_files:
                        m = re.search(r"photo_\d{4}-\d{2}-\d{2}_(\d{2}-\d{2})", img.name)
                        key = m.group(1) if m else "batch"
                        clusters.setdefault(key, []).append(img)

                    for idx, (batch_key, cluster_imgs) in enumerate(clusters.items(), 1):
                        dest_dir = RESOURCES_DIR / course_code / "exams" / "mid" / "2016"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        if len(clusters) == 1:
                            pdf_name = f"{subject_dir} Freshman Mid Exam ({len(cluster_imgs)} Pages).pdf"
                        else:
                            pdf_name = f"{subject_dir} Mid Exam Set {idx} ({len(cluster_imgs)} Pages).pdf"
                            
                        pdf_path = dest_dir / pdf_name
                        images_to_pdf(cluster_imgs, pdf_path)
                        total_compiled_exams += 1

    # --- Populate High Value Samples ---
    print("\n🎁 Generating Free Teaser Samples in Resources/samples/...")
    samples_dir = RESOURCES_DIR / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    samples_to_create = [
        ("MATH101", "worksheets", "Math for NS Worksheet 1 (Chapter 1).pdf", "MATH101 Sample - Chapter 1 Mathematics Worksheet.pdf"),
        ("PHYS101", "slides", "General physics ppt short note..pptx", "PHYS101 Sample - General Physics Key Summary.pptx"),
        ("ENGL101", "worksheets", "FLEN EXERCISE(1).pdf", "ENGL101 Sample - Communicative English Exercises.pdf"),
        ("GEOG101", "worksheets", "125 Geo chapter 1 multiple choice questions by project 30.docx", "GEOG101 Sample - 125 Geography Questions Bank.docx"),
        ("LOGI101", "worksheets", "Logic CT Exam practice.pdf", "LOGI101 Sample - Logic Exam Practice Sheet.pdf"),
        ("PSYC101", "worksheets", "500 psyco questions.pdf", "PSYC101 Sample - 500 Psychology Questions Practice.pdf"),
    ]

    for c_code, cat, src_name, sample_name in samples_to_create:
        src = RESOURCES_DIR / c_code / cat / src_name
        if src.exists():
            shutil.copy2(src, samples_dir / sample_name)
            print(f"   🎁 Added Free Sample: {sample_name}")

    print("\n" + "=" * 70)
    print("✅ FILE ORGANIZATION & COMPILATION COMPLETE!")
    print(f"   📁 Individual Resources Transferred: {total_copied}")
    print(f"   📄 Multi-Page Exam Booklets Created: {total_compiled_exams}")
    print("=" * 70)

if __name__ == "__main__":
    organize()
