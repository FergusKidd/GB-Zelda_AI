#!/usr/bin/env python3
"""
Simple PyBoy ROM test script
"""
import sys
import os
from pyboy import PyBoy

def test_rom(rom_path):
    """Test a ROM file with PyBoy"""
    if not os.path.exists(rom_path):
        print(f"❌ ROM file not found: {rom_path}")
        return False
    
    print(f"🎮 Testing ROM: {rom_path}")
    
    try:
        # Initialize PyBoy with SDL2 window
        pyboy = PyBoy(rom_path, window="SDL2")
        pyboy.set_emulation_speed(1.0)
        
        print("✅ PyBoy initialized successfully!")
        print("🎯 ROM is working! You should see a game window.")
        print("⌨️  Press Ctrl+C to exit")
        
        # Run for a few seconds to test
        frame_count = 0
        while frame_count < 300:  # About 5 seconds at 60fps
            pyboy.tick()
            frame_count += 1
        
        print("✅ ROM test completed successfully!")
        pyboy.stop()
        return True
        
    except Exception as e:
        print(f"❌ Error testing ROM: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_rom.py <path_to_rom>")
        print("Example: python test_rom.py roms/zelda.gb")
        print("Example: python test_rom.py /path/to/your/rom.gb")
        sys.exit(1)
    
    rom_path = sys.argv[1]
    success = test_rom(rom_path)
    
    if success:
        print("\n🎉 ROM is working! You can now use it with the AI player.")
    else:
        print("\n💡 Tips:")
        print("   - Make sure the ROM file exists")
        print("   - Check that it's a valid Game Boy ROM (.gb or .gbc)")
        print("   - Try a different ROM file")

if __name__ == "__main__":
    main()
