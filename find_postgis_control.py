#!/usr/bin/env python3
"""
Find PostGIS Control Files

This script searches for PostGIS .control files in the source directory
that we need to copy for the extension to work.
"""

import os
import sys
from pathlib import Path

def find_postgis_control():
    """Find PostGIS .control files in source directory"""
    
    print("🔍 Searching for PostGIS Control Files")
    print("=" * 45)
    
    # Source directory (where PostGIS is installed)
    postgis_source = Path("C:/Program Files/postgis-3.6.0rc2/postgis-3.6.0rc2")
    
    print(f"\n📁 Source directory: {postgis_source}")
    
    if not postgis_source.exists():
        print("❌ PostGIS source directory not found!")
        return False
    
    # Search for all .control files
    print(f"\n1️⃣ Searching for .control files...")
    control_files = list(postgis_source.rglob("*.control"))
    
    if not control_files:
        print("   ❌ No .control files found")
        return False
    
    print(f"   📋 Found {len(control_files)} .control files")
    
    # Show all .control files
    for i, file_path in enumerate(control_files, 1):
        print(f"   {i:2d}. {file_path.name}")
        print(f"      Path: {file_path}")
        print(f"      Size: {file_path.stat().st_size} bytes")
    
    # Look specifically for PostGIS .control files
    print(f"\n2️⃣ PostGIS .control files:")
    postgis_control_files = [f for f in control_files if 'postgis' in f.name.lower()]
    
    if postgis_control_files:
        for file_path in postgis_control_files:
            print(f"   ✅ {file_path.name}")
            print(f"      Path: {file_path}")
            print(f"      Size: {file_path.stat().st_size} bytes")
    else:
        print("   ❌ No PostGIS .control files found")
        
        # Check if there are any files with 'postgis' in the name
        print(f"\n3️⃣ Checking for any PostGIS files...")
        all_postgis_files = list(postgis_source.rglob("*postgis*"))
        
        if all_postgis_files:
            print(f"   📋 Found {len(all_postgis_files)} PostGIS-related files:")
            for file_path in all_postgis_files:
                print(f"      {file_path.name} ({file_path.suffix})")
        else:
            print("   ❌ No PostGIS files found at all")
    
    # Check if we need to look in subdirectories
    print(f"\n4️⃣ Checking subdirectories for PostGIS...")
    subdirs = [d for d in postgis_source.iterdir() if d.is_dir()]
    
    for subdir in subdirs:
        postgis_files_in_subdir = list(subdir.rglob("*postgis*"))
        if postgis_files_in_subdir:
            print(f"   📁 {subdir.name}: {len(postgis_files_in_subdir)} PostGIS files")
            for file_path in postgis_files_in_subdir:
                print(f"      {file_path.name} ({file_path.suffix})")
    
    return True

if __name__ == "__main__":
    success = find_postgis_control()
    sys.exit(0 if success else 1)

