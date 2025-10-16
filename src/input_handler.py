#!/usr/bin/env python3
"""
Simple input handler for Zelda AI Player
"""
import threading
import sys

class InputHandler:
    def __init__(self):
        self.ai_started = False
        self.should_quit = False
        self.input_thread = None
        
    def start(self):
        """Start the input handler thread."""
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
    def _input_loop(self):
        """Input loop running in separate thread."""
        try:
            while not self.should_quit:
                try:
                    user_input = input().strip().lower()
                    
                    # Start AI commands
                    if user_input == '' or user_input == 'start' or user_input == 's':
                        self.ai_started = True
                        print("🚀 AI decision-making started!")
                        print("🎮 AI is now controlling the game!")
                    
                    # Quit commands
                    elif user_input == 'q' or user_input == 'quit' or user_input == 'exit':
                        self.should_quit = True
                        print("👋 Quitting...")
                        break
                    
                    # Help command
                    elif user_input == 'help' or user_input == 'h':
                        self._show_help()
                    
                    # Pause/Resume AI
                    elif user_input == 'pause' or user_input == 'p':
                        if self.ai_started:
                            self.ai_started = False
                            print("⏸️  AI paused. Type 'resume' or 'r' to continue.")
                        else:
                            print("ℹ️  AI is not running. Type 'start' to begin.")
                    
                    elif user_input == 'resume' or user_input == 'r':
                        if not self.ai_started:
                            self.ai_started = True
                            print("▶️  AI resumed!")
                        else:
                            print("ℹ️  AI is already running.")
                    
                    # Status command
                    elif user_input == 'status' or user_input == 'info':
                        self._show_status()
                    
                    # Invalid command
                    else:
                        print(f"❓ Unknown command: '{user_input}'. Type 'help' for available commands.")
                        
                except EOFError:
                    break
                except KeyboardInterrupt:
                    self.should_quit = True
                    break
        except Exception as e:
            print(f"Input handler error: {e}")
            
    def stop(self):
        """Stop the input handler."""
        self.should_quit = True
