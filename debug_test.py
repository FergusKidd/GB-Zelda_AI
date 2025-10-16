#!/usr/bin/env python3
"""
Test script to debug the AI player
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv()

def test_timing():
    """Test the timing logic"""
    print("Testing timing logic...")
    
    decision_interval = 5.0
    last_decision_time = None
    
    for i in range(20):
        current_time = time.time()
        should_make_decision = last_decision_time is None or (current_time - last_decision_time) >= decision_interval
        
        if should_make_decision:
            print(f"Decision made at {i}: {current_time}")
            last_decision_time = current_time
        else:
            remaining = decision_interval - (current_time - last_decision_time)
            print(f"Frame {i}: {remaining:.2f}s until next decision")
        
        time.sleep(0.5)  # Simulate frame time

def test_input_handler():
    """Test the input handler"""
    print("\nTesting input handler...")
    from input_handler import InputHandler
    
    handler = InputHandler()
    handler.start()
    
    print("Input handler started. Try typing 'start' and then 'q'")
    
    # Wait for input
    while not handler.should_quit:
        if handler.ai_started:
            print("✅ AI started!")
            break
        time.sleep(0.1)
    
    handler.stop()
    print("Input handler stopped.")

if __name__ == "__main__":
    print("🔍 Debugging AI Player...")
    test_timing()
    test_input_handler()
