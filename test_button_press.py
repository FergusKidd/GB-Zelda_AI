#!/usr/bin/env python3
"""
Simple test to verify PyBoy button input works correctly.
This will test each button individually to see if Link moves.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from pyboy_client import PyBoyClient
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_button_input():
    """Test each button to see if Link moves."""
    config = Config()
    
    # Initialize PyBoy
    pyboy_client = PyBoyClient(config)
    if not pyboy_client.initialize():
        logger.error("Failed to initialize PyBoy")
        return False
    
    logger.info("🎮 PyBoy initialized successfully!")
    logger.info("🎮 Game window should be visible now")
    logger.info("🎮 Testing each button for 1 second...")
    
    # Test each button
    buttons = ['up', 'down', 'left', 'right', 'a', 'b', 'start', 'select']
    
    for button in buttons:
        logger.info(f"\n🔘 Testing {button.upper()} button...")
        
        # Test with explicit press/release
        logger.info(f"Testing explicit press/release for {button}...")
        
        # Press button
        if pyboy_client.press_button(button, delay=30):  # Hold for 30 frames (0.5 seconds)
            logger.info(f"✅ {button} pressed successfully")
        else:
            logger.error(f"❌ Failed to press {button}")
            continue
        
        # Wait a moment between buttons
        time.sleep(1)
    
    logger.info("\n🎮 Button test completed!")
    logger.info("🎮 Check the game window - did Link move for each button?")
    
    # Keep window open for a few more seconds
    logger.info("🎮 Keeping window open for 5 more seconds...")
    time.sleep(5)
    
    # Cleanup
    pyboy_client.cleanup()
    logger.info("🎮 Test completed!")

if __name__ == "__main__":
    test_button_input()
