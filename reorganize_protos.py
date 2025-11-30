#!/usr/bin/env python3
"""
Proto reorganization script for AI Pipestream
Restructures proto files to match package names and adds v1 versioning
Uses git mv to preserve file history
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

PROTO_ROOT = Path("src/main/proto")

def extract_package(proto_file: Path) -> str:
    """Extract package name from proto file"""
    with open(proto_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('package '):
                # Extract package name
                match = re.match(r'package\s+([\w.]+)\s*;', line)
                if match:
                    return match.group(1)
    return ""

def should_add_version(package: str) -> bool:
    """Determine if package should have v1 suffix added"""
    # Already has version
    if re.search(r'\.v\d+$', package):
        return False
    # Skip google packages
    if package.startswith('google.'):
        return False
    return True

def add_version_to_package(package: str) -> str:
    """Add v1 suffix to package if needed"""
    if should_add_version(package):
        return f"{package}.v1"
    return package

def package_to_path(package: str) -> Path:
    """Convert package name to directory path"""
    return Path(package.replace('.', '/'))

def analyze_proto_files() -> List[Tuple[Path, str, str, Path]]:
    """
    Analyze all proto files and return reorganization plan
    Returns: List of (current_path, old_package, new_package, new_path)
    """
    plan = []

    for proto_file in PROTO_ROOT.rglob("*.proto"):
        if proto_file.is_file():
            old_package = extract_package(proto_file)
            if not old_package:
                print(f"WARNING: No package found in {proto_file}")
                continue

            new_package = add_version_to_package(old_package)
            new_dir = PROTO_ROOT / package_to_path(new_package)
            new_path = new_dir / proto_file.name

            plan.append((proto_file, old_package, new_package, new_path))

    return plan

def update_package_in_file(file_path: Path, old_package: str, new_package: str):
    """Update package declaration in proto file"""
    if old_package == new_package:
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Update package declaration
    content = re.sub(
        rf'^package\s+{re.escape(old_package)}\s*;',
        f'package {new_package};',
        content,
        flags=re.MULTILINE
    )

    with open(file_path, 'w') as f:
        f.write(content)

def update_imports_in_all_files(package_map: Dict[str, str]):
    """Update all import statements to reflect new package names"""
    for proto_file in PROTO_ROOT.rglob("*.proto"):
        if not proto_file.is_file():
            continue

        with open(proto_file, 'r') as f:
            content = f.read()

        modified = False
        for old_pkg, new_pkg in package_map.items():
            if old_pkg == new_pkg:
                continue

            # Update imports that reference the old package
            old_pattern = re.escape(old_pkg)
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_pkg, content)
                modified = True

        if modified:
            with open(proto_file, 'w') as f:
                f.write(content)

def git_mv(src: Path, dest: Path):
    """Use git mv to move file preserving history"""
    # Create parent directory if it doesn't exist
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Use git mv
    result = subprocess.run(
        ['git', 'mv', str(src), str(dest)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"git mv failed: {result.stderr}")

def execute_reorganization(plan: List[Tuple[Path, str, str, Path]], dry_run: bool = True):
    """Execute the reorganization plan"""

    print("=" * 80)
    print("PROTO REORGANIZATION PLAN (Using git mv)")
    print("=" * 80)
    print()

    # Group by action type
    moves_needed = []
    package_updates = []
    no_change = []

    for current, old_pkg, new_pkg, target in plan:
        rel_current = current.relative_to(PROTO_ROOT)
        rel_target = target.relative_to(PROTO_ROOT)

        needs_move = rel_current != rel_target
        needs_pkg_update = old_pkg != new_pkg

        if needs_move or needs_pkg_update:
            if needs_move:
                moves_needed.append((current, old_pkg, new_pkg, target))
            elif needs_pkg_update:
                package_updates.append((current, old_pkg, new_pkg, target))
        else:
            no_change.append((current, old_pkg, new_pkg, target))

    print(f"📊 SUMMARY:")
    print(f"  Total files: {len(plan)}")
    print(f"  Need move + package update: {len(moves_needed)}")
    print(f"  Need package update only: {len(package_updates)}")
    print(f"  No changes needed: {len(no_change)}")
    print()

    if moves_needed:
        print(f"📁 FILES TO MOVE WITH GIT ({len(moves_needed)}):")
        print()
        for current, old_pkg, new_pkg, target in sorted(moves_needed)[:10]:  # Show first 10
            rel_current = current.relative_to(PROTO_ROOT)
            rel_target = target.relative_to(PROTO_ROOT)
            pkg_change = f" [{old_pkg} → {new_pkg}]" if old_pkg != new_pkg else ""
            print(f"  {rel_current}")
            print(f"    → {rel_target}{pkg_change}")
            print()
        if len(moves_needed) > 10:
            print(f"  ... and {len(moves_needed) - 10} more files")
            print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN - No changes made")
        print("Run with --execute to apply changes")
        print("=" * 80)
        return

    print("=" * 80)
    print("EXECUTING REORGANIZATION WITH GIT MV...")
    print("=" * 80)
    print()

    # Build package mapping for import updates
    package_map = {}
    for _, old_pkg, new_pkg, _ in plan:
        if old_pkg != new_pkg:
            package_map[old_pkg] = new_pkg

    # Step 1: Update package declarations in place (before moving)
    print("Step 1: Updating package declarations...")
    for current, old_pkg, new_pkg, _ in plan:
        if old_pkg != new_pkg:
            update_package_in_file(current, old_pkg, new_pkg)
            print(f"  ✓ Updated {current.relative_to(PROTO_ROOT)}")

    # Step 2: Move files using git mv
    print("\nStep 2: Moving files with git mv (preserves history)...")
    for current, _, _, target in moves_needed:
        try:
            git_mv(current, target)
            print(f"  ✓ git mv {current.relative_to(PROTO_ROOT)} → {target.relative_to(PROTO_ROOT)}")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            raise

    # Step 3: Update all imports
    print("\nStep 3: Updating import statements...")
    update_imports_in_all_files(package_map)
    print("  ✓ Updated imports in all files")

    print()
    print("=" * 80)
    print("✅ REORGANIZATION COMPLETE!")
    print("=" * 80)
    print()
    print("Next step: Test proto compilation with buf")

if __name__ == "__main__":
    import sys

    os.chdir("/home/krickert/IdeaProjects/ai-pipestream/feat/pipestream-protos-lint")

    plan = analyze_proto_files()

    dry_run = "--execute" not in sys.argv
    execute_reorganization(plan, dry_run=dry_run)
