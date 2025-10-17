#!/usr/bin/env python3
"""
Fresh Start Script
Wipes all saves, logs, and history to start a completely new game run.
"""
import os
import shutil
from pathlib import Path

def confirm_wipe():
    """Ask user to confirm before wiping data."""
    print("⚠️  WARNING: This will delete ALL game progress and logs!")
    print("   - PyBoy save states")
    print("   - Decision history")
    print("   - Story logs")
    print("   - Action history")
    print("   - All log files")
    print()
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    return response.lower() == 'yes'

def wipe_files():
    """Delete all save states and logs."""
    files_to_delete = [
        # Save states
        'logs/pyboy_save_state.state',
        
        # History files
        'logs/decision_history.json',
        'logs/story_log.json',
        
        # Log files
        'logs/zelda_ai.log',
    ]
    
    # Action history files (they have timestamps in filename)
    action_history_pattern = 'logs/action_history_*.json'
    
    deleted_count = 0
    
    # Delete specific files
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {file_path}: {e}")
        else:
            print(f"⏭️  Not found (already clean): {file_path}")
    
    # Delete action history files
    logs_dir = Path('logs')
    if logs_dir.exists():
        for action_file in logs_dir.glob('action_history_*.json'):
            try:
                action_file.unlink()
                print(f"✅ Deleted: {action_file}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {action_file}: {e}")
    
    return deleted_count

def main():
    """Main function."""
    print("=" * 60)
    print("🆕 Fresh Start Script - Zelda AI")
    print("=" * 60)
    print()
    
    # Check if logs directory exists
    if not os.path.exists('logs'):
        print("📁 No logs directory found - already starting fresh!")
        return
    
    # Confirm with user
    if not confirm_wipe():
        print("❌ Cancelled - no files were deleted.")
        return
    
    print()
    print("🗑️  Wiping data...")
    print()
    
    # Delete files
    deleted_count = wipe_files()
    
    print()
    print("=" * 60)
    print(f"✨ Fresh start complete! Deleted {deleted_count} file(s).")
    print("=" * 60)
    print()
    print("You can now run the game with:")
    print("  python main.py")
    print()

if __name__ == "__main__":
    main()

