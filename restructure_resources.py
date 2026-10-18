"""
restructure_resources.py
- Flattens exams/* (removes final/mid/year subdirs, keeps files in exams/)
- Deduplicates files (by name, keeps one copy)
- Renames folders:
    handwritten  -> TeachersGuide
    modules      -> module
    worksheets   -> worksheet
    slides       -> ppt
- Removes empty leftover directories
"""

import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESOURCES = Path("Resources")

FOLDER_RENAMES = {
    "handwritten": "TeachersGuide",
    "modules":     "module",
    "worksheets":  "worksheet",
    "slides":      "ppt",
    # exams stays as exams
}


def flatten_and_dedup(folder: Path):
    """
    Recursively collect all files inside folder (including subdirs),
    move them up to folder/, then delete all subdirs.
    If two files share the same name, keep whichever is already placed.
    """
    seen = set()

    # First pass: collect files already directly in folder/
    for f in folder.iterdir():
        if f.is_file():
            seen.add(f.name)

    # Second pass: walk subdirs and move files up
    for f in sorted(folder.rglob("*")):
        if f.is_file() and f.parent != folder:
            if f.name in seen:
                print(f"    [DEL-DUP] {f.relative_to(RESOURCES)}")
                f.unlink()
            else:
                dest = folder / f.name
                print(f"    [MOVE]    {f.relative_to(RESOURCES)} -> {dest.relative_to(RESOURCES)}")
                shutil.move(str(f), str(dest))
                seen.add(f.name)

    # Third pass: remove now-empty subdirectories (deepest first)
    for d in sorted(folder.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
                print(f"    [RMDIR]   {d.relative_to(RESOURCES)}")
            except OSError:
                pass  # not empty


def rename_folder(old: Path, new_name: str) -> Path:
    new = old.parent / new_name
    if old.name == new_name:
        return old
    if new.exists():
        # Merge: move all files from old into new, then delete old
        print(f"  [MERGE]  {old.name}/ -> {new_name}/")
        for f in old.iterdir():
            dest = new / f.name
            if dest.exists():
                print(f"    [DEL-DUP] {f.name}")
                if f.is_file():
                    f.unlink()
            else:
                shutil.move(str(f), str(dest))
        old.rmdir()
    else:
        print(f"  [RENAME] {old.name}/ -> {new_name}/")
        old.rename(new)
    return new


def remove_empty_dirs(root: Path):
    for d in sorted(root.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
                print(f"  [RMDIR-EMPTY] {d.relative_to(RESOURCES)}")
            except OSError:
                pass


def main():
    print("=" * 60)
    print("  Restructuring Resources/")
    print("=" * 60)

    for course_dir in sorted(RESOURCES.iterdir()):
        if not course_dir.is_dir():
            continue
        print(f"\n--- {course_dir.name} ---")

        for type_dir in sorted(course_dir.iterdir()):
            if not type_dir.is_dir():
                continue

            folder_name = type_dir.name

            # Step 1: Flatten all type folders (move files from subdirs up)
            print(f"  Flattening {folder_name}/")
            flatten_and_dedup(type_dir)

            # Step 2: Rename folder if needed
            new_name = FOLDER_RENAMES.get(folder_name, folder_name)
            type_dir = rename_folder(type_dir, new_name)

        # Step 3: Clean up any remaining empty dirs
        remove_empty_dirs(course_dir)

    print("\n" + "=" * 60)
    print("  Done! Final structure:")
    print("=" * 60)
    for course_dir in sorted(RESOURCES.iterdir()):
        if not course_dir.is_dir():
            continue
        print(f"\n{course_dir.name}/")
        for sub in sorted(course_dir.iterdir()):
            if sub.is_dir():
                files = [f for f in sub.iterdir() if f.is_file()]
                print(f"  {sub.name}/ ({len(files)} files)")
                for f in sorted(files):
                    print(f"    {f.name}")


if __name__ == "__main__":
    main()
