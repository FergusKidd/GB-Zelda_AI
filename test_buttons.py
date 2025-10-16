#!/usr/bin/env python3
"""
Test script to manually test button presses
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pyboy_client import PyBoyClient

load_dotenv()

def test_button_presses():
    """Test button presses manually"""
    print("🎮 Testing button presses...")
    
    # Initialize PyBoy
    rom_path = os.getenv('ROM_PATH', 'roms/zelda.gb')
    pyboy_client = PyBoyClient(rom_path, 1.0, "SDL2")
    
    if not pyboy_client.initialize():
        print("❌ Failed to initialize PyBoy")
        return
    
    print("✅ PyBoy initialized successfully!")
    print("🎮 Game window should be visible now!")
    print("⌨️  Testing button presses in 3 seconds...")
    
    time.sleep(3)
    
    # Test each button
    buttons_to_test = ['up', 'down', 'left', 'right', 'a', 'b', 'start', 'select']
    
    for button in buttons_to_test:
        print(f"\n🔘 Testing {button.upper()} button...")
        
        # Press button
        print(f"  Pressing {button}...")
        if pyboy_client.press_button(button):
            print(f"  ✅ Pressed {button}")
        else:
            print(f"  ❌ Failed to press {button}")
        
        # Hold for 0.5 seconds
        time.sleep(0.5)
        
        # Release button
        print(f"  Releasing {button}...")
        if pyboy_client.release_button(button):
            print(f"  ✅ Released {button}")
        else:
            print(f"  ❌ Failed to release {button}")
        
        # Wait between tests
        time.sleep(1)
    
    print("\n🎮 Button test completed!")
    print("👀 Check the game window to see if buttons were pressed!")
    
    # Keep game running for a bit
    print("⏰ Keeping game running for 10 seconds...")
    time.sleep(10)
    
    pyboy_client.close()
    print("✅ Test completed!")

if __name__ == "__main__":
    test_button_presses()
