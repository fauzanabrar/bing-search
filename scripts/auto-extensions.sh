#!/usr/bin/env python3
"""
Auto-import Violentmonkey scripts to all profiles
Extracts scripts from Profile 4 and injects them into other profiles
"""

import os
import json
import sqlite3
import shutil
from pathlib import Path

MERCURY_DIR = Path.home() / ".mercury"
SOURCE_PROFILE = MERCURY_DIR / "Profile 4"

def find_vm_storage(profile_path):
    """Find Violentmonkey's storage directory"""
    storage_dir = profile_path / "storage" / "default"
    if not storage_dir.exists():
        return None
    
    # Find moz-extension directory with VM data
    for ext_dir in storage_dir.glob("moz-extension*"):
        idb_dir = ext_dir / "idb"
        if idb_dir.exists():
            # Check if this is Violentmonkey's storage
            for db_file in idb_dir.glob("*.sqlite"):
                if "wleabcEoxlt-eengsairo" in db_file.name:
                    return ext_dir
    return None

def extract_vm_scripts(source_profile):
    """Extract Violentmonkey scripts from Profile 4"""
    vm_storage = find_vm_storage(source_profile)
    if not vm_storage:
        print("❌ Could not find Violentmonkey storage in Profile 4")
        return None
    
    print(f"✓ Found VM storage: {vm_storage.name}")
    
    # Find the database
    idb_dir = vm_storage / "idb"
    db_file = None
    for f in idb_dir.glob("*.sqlite"):
        if "wleabcEoxlt-eengsairo" in f.name:
            db_file = f
            break
    
    if not db_file:
        print("❌ Could not find Violentmonkey database")
        return None
    
    # Read scripts from database
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  Database tables: {[t[0] for t in tables]}")
        
        # Try to extract data
        cursor.execute("SELECT * FROM object_data")
        rows = cursor.fetchall()
        
        conn.close()
        
        print(f"  Found {len(rows)} data entries")
        return vm_storage
        
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return None

def copy_vm_storage(source_storage, target_profile):
    """Copy VM storage to target profile with new UUID"""
    target_storage_base = target_profile / "storage" / "default"
    target_storage_base.mkdir(parents=True, exist_ok=True)
    
    # Find existing VM storage in target
    existing_vm = find_vm_storage(target_profile)
    
    if existing_vm:
        # Copy to existing UUID
        print(f"    → Existing VM storage: {existing_vm.name}")
        
        # Copy IDB directory
        source_idb = source_storage / "idb"
        target_idb = existing_vm / "idb"
        
        if source_idb.exists():
            if target_idb.exists():
                shutil.rmtree(target_idb)
            shutil.copytree(source_idb, target_idb)
            print(f"    ✓ Copied scripts to {existing_vm.name}")
            return True
    else:
        # No VM storage yet, just copy the entire directory
        # (VM will get it when it initializes)
        new_storage = target_storage_base / source_storage.name
        if new_storage.exists():
            shutil.rmtree(new_storage)
        shutil.copytree(source_storage, new_storage)
        print(f"    ✓ Copied storage as {source_storage.name}")
        return True
    
    return False

def main():
    print("=" * 50)
    print("Violentmonkey Script Auto-Importer")
    print("=" * 50)
    print()
    
    if not SOURCE_PROFILE.exists():
        print("❌ Profile 4 not found")
        return
    
    # Extract scripts from Profile 4
    print("Extracting scripts from Profile 4...")
    vm_storage = extract_vm_scripts(SOURCE_PROFILE)
    
    if not vm_storage:
        print("\n❌ Failed to extract scripts")
        return
    
    print()
    
    # Find target profiles
    targets = []
    for p in MERCURY_DIR.glob("*Profile*"):
        if p.is_dir() and p != SOURCE_PROFILE:
            targets.append(p)
    for p in MERCURY_DIR.glob("*.default*"):
        if p.is_dir():
            targets.append(p)
    
    print(f"Found {len(targets)} target profiles")
    print()
    
    # Copy to each profile
    success_count = 0
    for target in targets:
        profile_name = target.name
        print(f"→ {profile_name}")
        
        if copy_vm_storage(vm_storage, target):
            success_count += 1
        else:
            print(f"    ✗ Failed")
        print()
    
    print("=" * 50)
    print(f"✅ Complete! Updated {success_count}/{len(targets)} profiles")
    print("=" * 50)
    print()
    print("Start Mercury with each profile to activate scripts")
    print()

if __name__ == "__main__":
    main()