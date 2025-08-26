#!/usr/bin/env python3
"""
Copy PostGIS Files to PostgreSQL Extension Directory

This script copies PostGIS extension files from the installed directory
to the PostgreSQL extension directory so PostgreSQL can find them.
"""

import shutil
import os
import sys
from pathlib import Path

def copy_postgis_files():
    """Copy PostGIS files to PostgreSQL extension directory"""
    
    print("🚀 Copying PostGIS Files to PostgreSQL Extension Directory")
    print("=" * 70)
    
    # Source directory (where PostGIS is installed)
    postgis_source = Path("C:/Program Files/postgis-3.6.0rc2/postgis-3.6.0rc2")
    
    # Target directory (PostgreSQL extension directory)
    postgres_target = Path("C:/Program Files/PostgreSQL/16/share/extension")
    
    print(f"\n📁 Source: {postgis_source}")
    print(f"📁 Target: {postgres_target}")
    
    # Check if source exists
    if not postgis_source.exists():
        print(f"❌ PostGIS source directory not found: {postgis_source}")
        print("💡 Please check the PostGIS installation path")
        return False
    
    # Check if target exists
    if not postgres_target.exists():
        print(f"❌ PostgreSQL extension directory not found: {postgres_target}")
        print("💡 Please check the PostgreSQL installation path")
        return False
    
    print(f"\n1️⃣ Checking PostGIS files in source directory...")
    
    # List files in source directory
    source_files = list(postgis_source.rglob("*"))
    print(f"   📋 Found {len(source_files)} files/directories")
    
    # Find PostGIS extension files
    extension_files = []
    for file_path in source_files:
        if file_path.is_file():
            if file_path.suffix in ['.control', '.sql', '.so', '.dll']:
                if 'postgis' in file_path.name.lower():
                    extension_files.append(file_path)
    
    print(f"   📋 Found {len(extension_files)} PostGIS extension files")
    
    if not extension_files:
        print("   ❌ No PostGIS extension files found")
        return False
    
    # Show what we'll copy
    print(f"\n2️⃣ PostGIS extension files to copy:")
    for file_path in extension_files:
        print(f"   📄 {file_path.name}")
    
    # Copy files
    print(f"\n3️⃣ Copying PostGIS files...")
    
    copied_count = 0
    for source_file in extension_files:
        try:
            # Determine target path
            relative_path = source_file.relative_to(postgis_source)
            target_file = postgres_target / relative_path.name
            
            # Create target directory if it doesn't exist
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_file, target_file)
            print(f"   ✅ Copied: {source_file.name}")
            copied_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to copy {source_file.name}: {e}")
    
    print(f"\n📊 Copy Summary:")
    print(f"   ✅ Successfully copied: {copied_count} files")
    print(f"   ❌ Failed: {len(extension_files) - copied_count} files")
    
    if copied_count > 0:
        print(f"\n🎉 PostGIS files copied successfully!")
        print(f"💡 You may need to restart PostgreSQL service for changes to take effect")
        print(f"🔧 Then run: python enable_postgis.py")
        return True
    else:
        print(f"\n❌ No files were copied successfully")
        return False

if __name__ == "__main__":
    success = copy_postgis_files()
    sys.exit(0 if success else 1)

