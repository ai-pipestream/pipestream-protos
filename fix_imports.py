#!/usr/bin/env python3
"""Fix all import paths to use new directory structure"""

import re
from pathlib import Path

PROTO_ROOT = Path("src/main/proto")

# Mapping of old import paths to new paths
IMPORT_FIXES = {
    'core/pipeline_core_types.proto': 'ai/pipestream/data/v1/pipeline_core_types.proto',
    'core/pipeline_config_models.proto': 'ai/pipestream/config/v1/pipeline_config_models.proto',
    'core/repository_service_data.proto': 'ai/pipestream/repository/v1/repository_service_data.proto',
    'module/module_service.proto': 'ai/pipestream/data/module/v1/module_service.proto',
    'opensearch-manager/opensearch_document.proto': 'ai/pipestream/opensearch/v1/opensearch_document.proto',
    # Tika metadata files
    'module/parser/tika/tika_base_metadata.proto': 'ai/pipestream/parsed/data/tika/base/v1/tika_base_metadata.proto',
    'module/parser/tika/dublin_core.proto': 'ai/pipestream/parsed/data/dublin/v1/dublin_core.proto',
    'module/parser/tika/office_metadata.proto': 'ai/pipestream/parsed/data/office/v1/office_metadata.proto',
    'module/parser/tika/pdf_metadata.proto': 'ai/pipestream/parsed/data/pdf/v1/pdf_metadata.proto',
    'module/parser/tika/image_metadata.proto': 'ai/pipestream/parsed/data/image/v1/image_metadata.proto',
    'module/parser/tika/email_metadata.proto': 'ai/pipestream/parsed/data/email/v1/email_metadata.proto',
    'module/parser/tika/media_metadata.proto': 'ai/pipestream/parsed/data/media/v1/media_metadata.proto',
    'module/parser/tika/html_metadata.proto': 'ai/pipestream/parsed/data/html/v1/html_metadata.proto',
    'module/parser/tika/rtf_metadata.proto': 'ai/pipestream/parsed/data/rtf/v1/rtf_metadata.proto',
    'module/parser/tika/database_metadata.proto': 'ai/pipestream/parsed/data/database/v1/database_metadata.proto',
    'module/parser/tika/font_metadata.proto': 'ai/pipestream/parsed/data/tika/font/v1/font_metadata.proto',
    'module/parser/tika/epub_metadata.proto': 'ai/pipestream/parsed/data/epub/v1/epub_metadata.proto',
    'module/parser/tika/warc_metadata.proto': 'ai/pipestream/parsed/data/warc/v1/warc_metadata.proto',
    'module/parser/tika/climate_forecast_metadata.proto': 'ai/pipestream/parsed/data/climate/v1/climate_forecast_metadata.proto',
    'module/parser/tika/creative_commons_metadata.proto': 'ai/pipestream/parsed/data/creative_commons/v1/creative_commons_metadata.proto',
    'module/parser/tika/generic_metadata.proto': 'ai/pipestream/parsed/data/generic/v1/generic_metadata.proto',
}

def fix_imports_in_file(file_path: Path):
    """Fix import paths in a single proto file"""
    with open(file_path, 'r') as f:
        content = f.read()

    original = content
    modified = False

    for old_path, new_path in IMPORT_FIXES.items():
        old_import = f'import "{old_path}"'
        new_import = f'import "{new_path}"'

        if old_import in content:
            content = content.replace(old_import, new_import)
            modified = True
            print(f"  {file_path.relative_to(PROTO_ROOT)}: {old_path} → {new_path}")

    if modified:
        with open(file_path, 'w') as f:
            f.write(content)

    return modified

def main():
    print("Fixing import paths...")
    print()

    fixed_count = 0
    for proto_file in PROTO_ROOT.rglob("*.proto"):
        if fix_imports_in_file(proto_file):
            fixed_count += 1

    print()
    print(f"✅ Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    import os
    os.chdir("/home/krickert/IdeaProjects/ai-pipestream/feat/pipestream-protos-lint")
    main()
