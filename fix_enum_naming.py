#!/usr/bin/env python3
"""
Fix enum naming issues in protobuf files according to buf lint standards.

Rules:
1. Enum values must be prefixed with ENUM_TYPE_NAME_
2. Zero value must be suffixed with _UNSPECIFIED
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Base directory for proto files
PROTO_BASE = Path("src/main/proto")

def get_enum_errors() -> List[str]:
    """Get all enum-related errors from buf lint."""
    result = subprocess.run(
        ["buf", "lint", "src/main/proto"],
        capture_output=True,
        text=True
    )
    errors = []
    # Buf outputs to STDOUT, not STDERR
    for line in result.stdout.splitlines():
        if "enum" in line.lower():
            errors.append(line)
    return errors

def parse_enum_error(error: str) -> Tuple[str, int, str, str]:
    """Parse an enum error line.

    Returns: (file_path, line_number, current_name, expected_prefix)
    """
    # Example: src/main/proto/ai/pipestream/data/module/v1/module_service.proto:93:3:Enum value name "PARSER" should be prefixed with "CAPABILITY_TYPE_".
    match = re.match(r'([^:]+):(\d+):\d+:Enum (?:zero )?value name "([^"]+)" should be (?:prefixed with|suffixed with) "([^"]+)"', error)
    if match:
        file_path = match.group(1)
        # Remove src/main/proto/ prefix if present
        if file_path.startswith("src/main/proto/"):
            file_path = file_path[len("src/main/proto/"):]
        line_num = int(match.group(2))
        current_name = match.group(3)
        expected_affix = match.group(4)
        return (file_path, line_num, current_name, expected_affix)
    return None

def find_enum_and_values(file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Find all enums in a file and their values with line numbers.

    Returns: {enum_name: [(line_num, value_name), ...]}
    """
    content = file_path.read_text()
    lines = content.splitlines()

    enums = {}
    current_enum = None
    brace_count = 0

    for i, line in enumerate(lines, 1):
        # Match enum definition
        enum_match = re.match(r'\s*enum\s+(\w+)\s*\{', line)
        if enum_match:
            current_enum = enum_match.group(1)
            enums[current_enum] = []
            brace_count = 1
            continue

        if current_enum:
            # Count braces
            brace_count += line.count('{') - line.count('}')

            # Match enum value
            value_match = re.match(r'\s*(\w+)\s*=\s*\d+;', line)
            if value_match:
                value_name = value_match.group(1)
                enums[current_enum].append((i, value_name))

            # End of enum
            if brace_count == 0:
                current_enum = None

    return enums

def convert_enum_name_to_prefix(enum_name: str) -> str:
    """Convert PascalCase enum name to SCREAMING_SNAKE_CASE prefix.

    Examples:
    - ControlCommand -> CONTROL_COMMAND_
    - CapabilityType -> CAPABILITY_TYPE_
    - Intent -> INTENT_
    """
    # Insert underscore before capitals (except first)
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', enum_name)
    return snake.upper() + '_'

def fix_enum_values(file_path: Path, enum_name: str, values_to_fix: List[Tuple[int, str, str]]):
    """Fix enum values in a file.

    Args:
        file_path: Path to the proto file
        enum_name: Name of the enum
        values_to_fix: List of (line_num, old_name, new_name) tuples
    """
    content = file_path.read_text()
    lines = content.splitlines(keepends=True)

    # Sort by line number in reverse to avoid line number shifts
    for line_num, old_name, new_name in sorted(values_to_fix, reverse=True):
        idx = line_num - 1
        lines[idx] = lines[idx].replace(old_name, new_name)

    file_path.write_text(''.join(lines))

def main():
    print("Analyzing enum errors...")
    errors = get_enum_errors()
    print(f"Found {len(errors)} enum errors\n")

    # Group errors by file
    file_errors: Dict[str, List[Tuple[int, str, str]]] = {}

    for error in errors:
        parsed = parse_enum_error(error)
        if not parsed:
            continue

        file_path, line_num, current_name, expected_affix = parsed

        if file_path not in file_errors:
            file_errors[file_path] = []

        file_errors[file_path].append((line_num, current_name, expected_affix))

    print(f"Errors span {len(file_errors)} files\n")

    # Process each file
    for rel_path, errors in file_errors.items():
        file_path = PROTO_BASE / rel_path
        print(f"\n{'='*80}")
        print(f"Processing: {rel_path}")
        print(f"{'='*80}")

        if not file_path.exists():
            print(f"  ⚠️  File not found, skipping")
            continue

        # Find all enums in this file
        enums = find_enum_and_values(file_path)

        # Group errors by enum
        fixes: Dict[str, List[Tuple[int, str, str]]] = {}

        for line_num, current_name, expected_affix in errors:
            # Find which enum this value belongs to
            enum_name = None
            for ename, values in enums.items():
                for vline, vname in values:
                    if vline == line_num and vname == current_name:
                        enum_name = ename
                        break
                if enum_name:
                    break

            if not enum_name:
                print(f"  ⚠️  Could not find enum for {current_name} at line {line_num}")
                continue

            if enum_name not in fixes:
                fixes[enum_name] = []

            # Determine new name
            if "_UNSPECIFIED" in expected_affix:
                # This is a zero value that needs _UNSPECIFIED suffix
                prefix = convert_enum_name_to_prefix(enum_name)
                new_name = f"{prefix}UNSPECIFIED"
            elif expected_affix.endswith('_'):
                # Need to add prefix
                # Remove existing prefix if present
                prefix = expected_affix
                if current_name.startswith(prefix):
                    new_name = current_name  # Already has prefix
                else:
                    # Check if it has a partial prefix
                    parts = prefix.rstrip('_').split('_')
                    current_parts = current_name.split('_')

                    # Remove any matching prefix parts
                    while current_parts and parts and current_parts[0] == parts[0]:
                        current_parts.pop(0)
                        parts.pop(0)

                    remainder = '_'.join(current_parts)
                    new_name = f"{prefix}{remainder}"
            else:
                print(f"  ⚠️  Unexpected affix pattern: {expected_affix}")
                continue

            if current_name != new_name:
                fixes[enum_name].append((line_num, current_name, new_name))
                print(f"  {enum_name}.{current_name} → {new_name}")

        # Apply fixes
        if fixes:
            all_fixes = []
            for enum_fixes in fixes.values():
                all_fixes.extend(enum_fixes)
            fix_enum_values(file_path, None, all_fixes)
            print(f"  ✓ Applied {len(all_fixes)} fixes")

    print(f"\n{'='*80}")
    print("Enum naming fixes complete!")
    print(f"{'='*80}\n")

    # Verify
    print("Running buf lint to verify...")
    result = subprocess.run(["buf", "lint", "src/main/proto"], capture_output=True, text=True)
    remaining_enum_errors = sum(1 for line in result.stdout.splitlines() if 'enum' in line.lower())
    print(f"Remaining enum errors: {remaining_enum_errors}")

if __name__ == "__main__":
    main()
