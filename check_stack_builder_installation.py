#!/usr/bin/env python3
"""
Check Stack Builder PostGIS Installation

This script checks what PostGIS files were actually installed
by Stack Builder and where they are located.
"""

import os
import sys
from pathlib import Path
import subprocess

def check_postgis_installation():
    """Check PostGIS installation status"""
    
    print("🔍 Checking Stack Builder PostGIS Installation")
    print("=" * 55)
    
    # Common PostgreSQL installation paths
    postgres_paths = [
        r"C:\Program Files\PostgreSQL\17",
        r"C:\Program Files\PostgreSQL\16",
        r"C:\Program Files\PostgreSQL\15",
        r"C:\Program Files\PostgreSQL\14",
        r"C:\Program Files\PostgreSQL\13",
        r"C:\Program Files\PostgreSQL\12",
        r"C:\Program Files\PostgreSQL\11",
        r"C:\Program Files\PostgreSQL\10"
    ]
    
    # Common PostGIS installation paths
    postgis_paths = [
        r"C:\Program Files\PostGIS",
        r"C:\Program Files\postgis",
        r"C:\Program Files\postgis-3.6.0rc2",
        r"C:\Program Files\postgis-3.6.0",
        r"C:\Program Files\postgis-3.5.0",
        r"C:\Program Files\postgis-3.4.0",
        r"C:\Program Files\postgis-3.3.0",
        r"C:\Program Files\postgis-3.2.0",
        r"C:\Program Files\postgis-3.1.0",
        r"C:\Program Files\postgis-3.0.0"
    ]
    
    print("\n1️⃣ Checking PostgreSQL installation paths...")
    postgres_found = []
    
    for path in postgres_paths:
        if os.path.exists(path):
            print(f"   ✅ Found: {path}")
            postgres_found.append(path)
            
            # Check extension directory
            ext_path = os.path.join(path, "share", "extension")
            if os.path.exists(ext_path):
                print(f"      📁 Extensions: {ext_path}")
                
                # Look for PostGIS files
                postgis_files = []
                for file in os.listdir(ext_path):
                    if 'postgis' in file.lower():
                        postgis_files.append(file)
                
                if postgis_files:
                    print(f"      🎯 PostGIS files found: {postgis_files}")
                else:
                    print(f"      ❌ No PostGIS files found")
            else:
                print(f"      ❌ Extensions directory not found")
        else:
            print(f"   ❌ Not found: {path}")
    
    print(f"\n2️⃣ Checking PostGIS installation paths...")
    postgis_found = []
    
    for path in postgis_paths:
        if os.path.exists(path):
            print(f"   ✅ Found: {path}")
            postgis_found.append(path)
            
            # List contents
            try:
                contents = os.listdir(path)
                print(f"      📁 Contents: {len(contents)} items")
                
                # Look for key files
                key_files = []
                for item in contents:
                    if any(keyword in item.lower() for keyword in ['postgis', 'spatial', 'geometry']):
                        key_files.append(item)
                
                if key_files:
                    print(f"      🎯 Key files: {key_files}")
            except PermissionError:
                print(f"      ⚠️ Permission denied accessing contents")
        else:
            print(f"   ❌ Not found: {path}")
    
    print(f"\n3️⃣ Checking system PATH for PostGIS...")
    
    # Check if postgis is in PATH
    try:
        result = subprocess.run(['postgis', '--version'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"   ✅ PostGIS found in PATH: {result.stdout.strip()}")
        else:
            print(f"   ❌ PostGIS not found in PATH")
    except FileNotFoundError:
        print(f"   ❌ PostGIS command not found")
    
    print(f"\n4️⃣ Checking registry for PostGIS...")
    
    # Try to check Windows registry
    try:
        import winreg
        
        # Check common registry keys
        registry_keys = [
            r"SOFTWARE\PostgreSQL\Installations",
            r"SOFTWARE\PostGIS",
            r"SOFTWARE\WOW6432Node\PostgreSQL\Installations",
            r"SOFTWARE\WOW6432Node\PostGIS"
        ]
        
        for key_path in registry_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    print(f"   ✅ Registry key found: {key_path}")
                    
                    # Try to enumerate values
                    try:
                        i = 0
                        while True:
                            name, value, type_ = winreg.EnumValue(key, i)
                            if 'postgis' in str(value).lower():
                                print(f"      🎯 PostGIS value: {name} = {value}")
                            i += 1
                    except WindowsError:
                        pass  # No more values
                        
            except FileNotFoundError:
                print(f"   ❌ Registry key not found: {key_path}")
            except PermissionError:
                print(f"   ⚠️ Permission denied accessing registry: {key_path}")
                
    except ImportError:
        print(f"   ⚠️ winreg module not available")
    
    print(f"\n5️⃣ Summary and Recommendations...")
    print("=" * 40)
    
    if postgres_found:
        print(f"   ✅ PostgreSQL installations found: {len(postgres_found)}")
        for path in postgres_found:
            print(f"      📍 {path}")
    
    if postgis_found:
        print(f"   ✅ PostGIS installations found: {len(postgis_found)}")
        for path in postgis_found:
            print(f"      📍 {path}")
    
    if not postgis_found:
        print(f"   ❌ No PostGIS installations found")
        print(f"   💡 Recommendations:")
        print(f"      1. Check if Stack Builder installation completed successfully")
        print(f"      2. Verify PostGIS was selected during installation")
        print(f"      3. Try running Stack Builder as Administrator")
        print(f"      4. Check Stack Builder logs for installation errors")
    
    print(f"\n🔧 Next Steps:")
    if postgis_found:
        print(f"   1. Copy PostGIS files to PostgreSQL extension directory")
        print(f"   2. Restart PostgreSQL service")
        print(f"   3. Test PostGIS extension")
    else:
        print(f"   1. Re-run Stack Builder as Administrator")
        print(f"   2. Ensure PostGIS is selected for installation")
        print(f"   3. Check installation logs for errors")

if __name__ == "__main__":
    check_postgis_installation()
