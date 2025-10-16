"""
Main game loop that orchestrates screen capture, AI decision-making, and player control.
"""
import os
import sys
import time
import asyncio
import logging
import threading
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pyboy_client import PyBoyClient
from azure_client import AzureOpenAIClient
from screen_capture import ScreenCapture
from local_controller import LocalController
from input_handler import InputHandler
from history_manager import HistoryManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/zelda_ai.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ZeldaAIPlayer:
    """Main class that orchestrates the AI playing Zelda."""
    
    def __init__(self):
        """Initialize the AI player."""
        self.pyboy_client: Optional[PyBoyClient] = None
        self.azure_client: Optional[AzureOpenAIClient] = None
        self.screen_capture: Optional[ScreenCapture] = None
        self.local_controller: Optional[LocalController] = None
        self.input_handler: Optional[InputHandler] = None
        self.history_manager: Optional[HistoryManager] = None
        
        # Configuration
        self.rom_path = os.getenv('ROM_PATH', 'roms/zelda.gb')
        self.game_speed = float(os.getenv('GAME_SPEED', '1.0'))
        self.max_frames = int(os.getenv('MAX_FRAMES', '10000'))
        # Timing configuration
        self.decision_interval = float(os.getenv('DECISION_INTERVAL', '10.0'))  # Make decision every N seconds
        self.last_decision_time = None
        self.ai_task = None  # Track async AI task
        self.ai_processing = False  # Flag to prevent overlapping AI calls
        self.use_history_context = os.getenv('USE_HISTORY_CONTEXT', 'true').lower() == 'true'  # Enable/disable history
        
        # State tracking
        self.frame_count = 0
        self.decision_count = 0
        self.start_time = None
        self.is_running = False
        self.ai_started = False
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.debug("Initializing Zelda AI Player...")
            
            # Initialize PyBoy client
            logger.debug("Initializing PyBoy client...")
            window_type = os.getenv('WINDOW_TYPE', 'SDL2')
            self.pyboy_client = PyBoyClient(self.rom_path, self.game_speed, window_type)
            if not self.pyboy_client.initialize():
                logger.error("Failed to initialize PyBoy client")
                return False
            
            # Initialize Azure OpenAI client
            logger.debug("Initializing Azure OpenAI client...")
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
            azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
            
            if not all([azure_endpoint, azure_api_key, azure_deployment]):
                logger.error("Missing Azure OpenAI configuration")
                return False
            
            self.azure_client = AzureOpenAIClient(
                azure_endpoint, azure_api_key, azure_api_version, azure_deployment
            )
            
            # Test Azure connection
            if not self.azure_client.test_connection():
                logger.error("Failed to connect to Azure OpenAI")
                return False
            
            # Initialize screen capture
            logger.debug("Initializing screen capture...")
            self.screen_capture = ScreenCapture()
            
            # Initialize local controller
            logger.debug("Initializing local controller...")
            self.local_controller = LocalController(self.pyboy_client)
            
            # Initialize input handler
            logger.debug("Initializing input handler...")
            self.input_handler = InputHandler()
            
            # Initialize history manager
            logger.debug("Initializing history manager...")
            self.history_manager = HistoryManager(max_decisions=10)
            self.history_manager.load_from_file()  # Load existing history
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def run(self):
        """Run the main game loop."""
        if not self.initialize():
            logger.error("Initialization failed, exiting")
            return
        
        logger.info("🎮 Starting Zelda AI Player...")
        logger.info(f"⏰ AI decisions every {self.decision_interval}s | Type 'start' to begin | 'q' to quit")
        
        # Start input handler
        self.input_handler.start()
        
        # Run the main loop with asyncio
        asyncio.run(self._run_async())
    
    async def _run_async(self):
        """Async version of the main game loop."""
        self.start_time = time.time()
        self.is_running = True
        self.ai_started = False
        
        try:
            while self.is_running and self.frame_count < self.max_frames:
                # Advance game frame (skip if executing input to prevent interference)
                if not self.pyboy_client.is_executing_input:
                    if not self.pyboy_client.tick():
                        logger.warning("Game stopped running")
                        break
                else:
                    # Skip ticking during input execution
                    pass
                
                self.frame_count += 1
                
                # Check for input to start AI
                if not self.ai_started:
                    self.ai_started = self.input_handler.ai_started
                    if self.input_handler.should_quit:
                        self.is_running = False
                        break
                    # Show reminder every 5 seconds
                    if self.frame_count % 300 == 0:  # 5 seconds at 60fps
                        logger.debug("⌨️  Waiting for input... Type 'start' or press ENTER to start AI")
                    # Continue running the game but don't make AI decisions yet
                    await asyncio.sleep(0.01)
                    continue
                
                # Make decision at specified time intervals (only after AI starts)
                current_time = time.time()
                if self.last_decision_time is None or (current_time - self.last_decision_time) >= self.decision_interval:
                    # Start async AI decision if not already processing
                    if not self.ai_processing:
                        self.ai_task = asyncio.create_task(self._make_decision_async())
                        self.last_decision_time = current_time
                
                # Check if AI task completed and get result
                if self.ai_task and self.ai_task.done():
                    try:
                        result = self.ai_task.result()
                        if result:
                            logger.debug("✅ AI decision executed successfully")
                        else:
                            logger.warning("⚠️  AI decision failed")
                    except Exception as e:
                        logger.error(f"❌ AI decision error: {e}")
                    finally:
                        self.ai_task = None
                        self.ai_processing = False
                
                # Log progress periodically
                if self.frame_count % 100 == 0:
                    self._log_progress()
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.debug("Received interrupt signal, stopping...")
        except Exception as e:
            logger.error(f"Error in async main loop: {e}")
        finally:
            self._cleanup()
    
    async def _make_decision_async(self):
        """Make an AI decision asynchronously to prevent game pausing."""
        try:
            self.ai_processing = True
            logger.debug("🤖 Starting async AI decision...")
            
            # Capture current screen
            raw_screen = self.pyboy_client.get_screen_image()
            if raw_screen is None:
                logger.warning("Failed to capture screen")
                return False
            
            # Process screen for AI analysis
            processed_screen = self.screen_capture.process_frame(raw_screen)
            
            # Get current game state
            game_state = self.pyboy_client.get_game_state()
            
            # Get AI decision (this is the slow part - now async)
            history_context = self.history_manager.get_context_for_ai() if self.use_history_context else None
            decision = await asyncio.get_event_loop().run_in_executor(
                None, self.azure_client.get_game_decision, processed_screen, game_state, history_context
            )
            
            if decision is None:
                logger.warning("Failed to get AI decision")
                return False
            
            # Execute the decision
            success = self.local_controller.execute_decision(decision)
            
            self.decision_count += 1
            
            # Log essential decision info only
            sequence = decision.get('sequence', [])
            actions = [action['button'] for action in sequence]
            reasoning = decision.get('reasoning', 'No reasoning')
            chatgpt_text = decision.get('screen_text', '').strip()
            
            logger.info(f"🤖 #{self.decision_count}: {reasoning}")
            logger.info(f"🎮 Actions: {', '.join(actions)}")
            if chatgpt_text:
                logger.info(f"📖 Text: \"{chatgpt_text}\"")
            
            # Record decision in history
            self.history_manager.add_decision(decision, success, game_state)
            
            # Add story events if ChatGPT detected text
            chatgpt_text = decision.get('screen_text', '').strip()
            if chatgpt_text:
                self.history_manager.add_story_event('dialogue', chatgpt_text, {
                    'in_text_box': game_state.get('in_text_box', False),
                    'decision_id': self.decision_count,
                    'source': 'chatgpt'
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error in async AI decision: {e}")
            return False
        finally:
            self.ai_processing = False
    
    def _make_decision(self):
        """Make an AI decision and execute it."""
        try:
            # Capture current screen
            raw_screen = self.pyboy_client.get_screen_image()
            if raw_screen is None:
                logger.warning("Failed to capture screen")
                return
            
            # Process screen for AI analysis
            processed_screen = self.screen_capture.process_frame(raw_screen)
            
            # Get current game state
            game_state = self.pyboy_client.get_game_state()
            
            # Get AI decision
            decision = self.azure_client.get_game_decision(processed_screen, game_state)
            if decision is None:
                logger.warning("Failed to get AI decision")
                return
            
            # Execute the decision
            success = self.local_controller.execute_decision(decision)
            
            self.decision_count += 1
            
            # Log decision
            sequence_length = len(decision.get('sequence', []))
            logger.info(f"Decision #{self.decision_count}: {sequence_length} actions "
                       f"(confidence: {decision['confidence']:.2f}, success: {success})")
            
            # Log the actual sequence for debugging
            sequence = decision.get('sequence', [])
            logger.info(f"🎮 Executing sequence: {sequence}")
            
            # Save frame for debugging (occasionally)
            if self.decision_count % 50 == 0:
                debug_filename = f"logs/debug_frame_{self.decision_count}.png"
                self.screen_capture.save_frame(processed_screen, debug_filename)
            
        except Exception as e:
            logger.error(f"Error making decision: {e}")
    
    def _log_progress(self):
        """Log current progress and statistics."""
        try:
            elapsed_time = time.time() - self.start_time
            fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
            
            # Get action statistics
            stats = self.local_controller.get_action_statistics()
            
            logger.debug(f"Progress: {self.frame_count}/{self.max_frames} frames "
                       f"({fps:.1f} fps, {elapsed_time:.1f}s elapsed)")
            logger.debug(f"Decisions made: {self.decision_count}")
            
            if stats:
                logger.debug(f"Action success rate: {stats.get('total_actions', 0)} total actions")
                
                # Log top actions
                action_counts = stats.get('action_counts', {})
                if action_counts:
                    top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                    logger.debug(f"Top actions: {top_actions}")
            
        except Exception as e:
            logger.error(f"Error logging progress: {e}")
    
    def _cleanup(self):
        """Clean up resources."""
        try:
            logger.debug("Cleaning up resources...")
            
            # Restore terminal settings
            if hasattr(self, 'old_settings'):
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            
            # Save final statistics
            if self.local_controller:
                stats = self.local_controller.get_action_statistics()
                if stats:
                    logger.debug("Final statistics:")
                    logger.debug(f"Total decisions: {stats.get('total_actions', 0)}")
                    
                    # Log success rates by action
                    success_rates = stats.get('success_rates', {})
                    for action, rate in success_rates.items():
                        logger.debug(f"{action}: {rate:.2%} success rate")
            
            # Save action history
            if self.local_controller:
                history_filename = f"logs/action_history_{int(time.time())}.json"
                self.local_controller.save_action_history(history_filename)
            
            # Save history
            if self.history_manager:
                self.history_manager.save_to_file()
                logger.debug("History saved to files")
            
            # Close PyBoy
            if self.pyboy_client:
                self.pyboy_client.close()
            
            logger.debug("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def stop(self):
        """Stop the AI player."""
        logger.debug("Stopping AI player...")
        self.is_running = False


def main():
    """Main entry point."""
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Create and run AI player
    ai_player = ZeldaAIPlayer()
    
    try:
        ai_player.run()
    except KeyboardInterrupt:
        logger.debug("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        ai_player.stop()


if __name__ == "__main__":
    main()
