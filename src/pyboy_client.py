"""
PyBoy integration for running Zelda ROM and capturing screen data.
"""
import os
import logging
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
from PIL import Image
from pyboy import PyBoy
from pyboy.utils import WindowEvent
from text_extractor import TextExtractor

logger = logging.getLogger(__name__)

# Enable PyBoy's internal logging for crash diagnostics
pyboy_logger = logging.getLogger('pyboy')
pyboy_logger.setLevel(logging.DEBUG)


class PyBoyClient:
    """Client for managing PyBoy emulation and screen capture."""
    
    def __init__(self, rom_path: str, game_speed: float = 1.0, window_type: str = "SDL2"):
        """
        Initialize PyBoy client.
        
        Args:
            rom_path: Path to the Zelda ROM file
            game_speed: Game speed multiplier (1.0 = normal speed)
            window_type: Window type ("SDL2", "headless", or "OpenGL")
        """
        self.rom_path = rom_path
        self.game_speed = game_speed
        self.window_type = window_type
        self.is_executing_input = False  # Flag to prevent main loop interference
        self.text_extractor = TextExtractor()  # For extracting text from screens
        self.pyboy: Optional[PyBoy] = None
        self.screen_width = 160
        self.screen_height = 144
        self.save_state_file = "logs/pyboy_save_state.state"
        
    def initialize(self, try_load_state: bool = True) -> bool:
        """
        Initialize PyBoy with the ROM.
        
        Args:
            try_load_state: Whether to try loading a saved state
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not os.path.exists(self.rom_path):
                logger.error(f"ROM file not found: {self.rom_path}")
                return False
                
            self.pyboy = PyBoy(self.rom_path, window=self.window_type)
            self.pyboy.set_emulation_speed(self.game_speed)
            
            # Try to load save state first (before boot sequence)
            state_loaded = False
            if try_load_state and os.path.exists(self.save_state_file):
                try:
                    with open(self.save_state_file, "rb") as f:
                        self.pyboy.load_state(f)
                    logger.info(f"📂 ✅ Resumed from save state: {self.save_state_file}")
                    state_loaded = True
                except Exception as e:
                    logger.warning(f"Failed to load save state, starting fresh: {e}")
                    state_loaded = False
            
            # If no state loaded, skip initial boot sequence
            if not state_loaded:
                logger.info("🆕 Starting new game (no save state loaded)")
                for _ in range(60):  # Wait for boot
                    self.pyboy.tick()
                
            logger.info(f"PyBoy initialized successfully with ROM: {self.rom_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PyBoy: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log full stack trace for debugging
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            return False
    
    def get_screen_image(self) -> Optional[np.ndarray]:
        """
        Capture the current screen as a numpy array.
        
        Returns:
            Screen image as numpy array (RGB format) or None if failed
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized")
            return None
            
        try:
            # Get screen as PIL Image
            screen_image = self.pyboy.screen.image
            
            # Convert to numpy array
            screen_array = np.array(screen_image)
            
            # Ensure RGB format
            if len(screen_array.shape) == 3 and screen_array.shape[2] == 3:
                return screen_array
            else:
                # Convert grayscale to RGB
                if len(screen_array.shape) == 2:
                    screen_array = np.stack([screen_array] * 3, axis=-1)
                return screen_array
                
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")
            return None
    
    def press_button(self, button: str, delay: int = 0) -> bool:
        """
        Press a button on the Game Boy.
        
        Args:
            button: Button name ('up', 'down', 'left', 'right', 'a', 'b', 'start', 'select')
            delay: Number of frames to hold the button (0 = press and release immediately)
            
        Returns:
            True if button press successful, False otherwise
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized")
            return False
            
        button_map = {
            'up': WindowEvent.PRESS_ARROW_UP,
            'down': WindowEvent.PRESS_ARROW_DOWN,
            'left': WindowEvent.PRESS_ARROW_LEFT,
            'right': WindowEvent.PRESS_ARROW_RIGHT,
            'a': WindowEvent.PRESS_BUTTON_A,
            'b': WindowEvent.PRESS_BUTTON_B,
            'start': WindowEvent.PRESS_BUTTON_START,
            'select': WindowEvent.PRESS_BUTTON_SELECT,
        }
        
        if button not in button_map:
            logger.error(f"Unknown button: {button}")
            return False
            
        try:
            logger.debug(f"🔘 Sending button press: {button} (delay: {delay} frames)")
            
            # Send press input
            self.pyboy.send_input(button_map[button])
            
            # Process the input for the specified duration
            for _ in range(delay):
                self.pyboy.tick()
            
            # Send release input
            release_map = {
                'up': WindowEvent.RELEASE_ARROW_UP,
                'down': WindowEvent.RELEASE_ARROW_DOWN,
                'left': WindowEvent.RELEASE_ARROW_LEFT,
                'right': WindowEvent.RELEASE_ARROW_RIGHT,
                'a': WindowEvent.RELEASE_BUTTON_A,
                'b': WindowEvent.RELEASE_BUTTON_B,
                'start': WindowEvent.RELEASE_BUTTON_START,
                'select': WindowEvent.RELEASE_BUTTON_SELECT,
            }
            self.pyboy.send_input(release_map[button])
            
            logger.debug(f"✅ Button press completed: {button} for {delay} frames")
            return True
        except Exception as e:
            logger.error(f"Failed to press button {button}: {e}")
            return False
    
    def release_button(self, button: str) -> bool:
        """
        Release a button on the Game Boy.
        
        Args:
            button: Button name ('up', 'down', 'left', 'right', 'a', 'b', 'start', 'select')
            
        Returns:
            True if button release successful, False otherwise
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized")
            return False
            
        button_map = {
            'up': WindowEvent.RELEASE_ARROW_UP,
            'down': WindowEvent.RELEASE_ARROW_DOWN,
            'left': WindowEvent.RELEASE_ARROW_LEFT,
            'right': WindowEvent.RELEASE_ARROW_RIGHT,
            'a': WindowEvent.RELEASE_BUTTON_A,
            'b': WindowEvent.RELEASE_BUTTON_B,
            'start': WindowEvent.RELEASE_BUTTON_START,
            'select': WindowEvent.RELEASE_BUTTON_SELECT,
        }
        
        if button not in button_map:
            logger.error(f"Unknown button: {button}")
            return False
            
        try:
            logger.info(f"🔘 Sending button release: {button}")
            self.pyboy.send_input(button_map[button])
            self.pyboy.tick()  # Process the input immediately
            logger.info(f"✅ Button release sent successfully: {button}")
            return True
        except Exception as e:
            logger.error(f"Failed to release button {button}: {e}")
            return False
    
    def execute_sequence(self, sequence: List[Dict[str, Any]]) -> bool:
        """
        Execute a sequence of button presses using PyBoy's delay parameter.
        This is more efficient than separate press/release calls.
        
        Args:
            sequence: List of button actions with duration
            
        Returns:
            True if successful, False otherwise
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized")
            return False
            
        try:
            self.is_executing_input = True  # Prevent main loop interference
            logger.debug(f"🎮 Executing: {len(sequence)} actions")
            
            for i, action in enumerate(sequence):
                button = action['button']
                duration_frames = action['duration']
                delay_frames = action.get('delay', 0)
                
                # Cap durations for better responsiveness
                if button in ['up', 'down', 'left', 'right']:
                    # Movement buttons: cap at 15 frames (0.25 seconds)
                    duration_frames = min(duration_frames, 15)
                elif button == 'a':
                    # A button: cap at 5 frames (0.08 seconds) for quick presses
                    duration_frames = min(duration_frames, 5)
                else:
                    # Other buttons: cap at 10 frames (0.17 seconds)
                    duration_frames = min(duration_frames, 10)
                
                logger.debug(f"🎮 Action {i+1}/{len(sequence)}: {button.upper()} for {duration_frames} frames (capped)")
                
                # Use PyBoy's delay parameter for precise timing
                if not self.press_button(button, delay=duration_frames):
                    logger.error(f"Failed to execute action: {action}")
                    return False
                
                # Wait for delay between actions (also cap delays)
                if delay_frames > 0:
                    delay_frames = min(delay_frames, 5)  # Cap delay at 5 frames
                    logger.debug(f"⏱️  Waiting {delay_frames} frames between actions")
                    for _ in range(delay_frames):
                        self.pyboy.tick()
            
            # Ensure all inputs are fully processed
            logger.debug("🔄 Processing final inputs...")
            for _ in range(3):  # Reduced from 5 to 3 ticks
                self.pyboy.tick()
            
            logger.debug(f"✅ Completed: {len(sequence)} actions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute sequence: {e}")
            return False
        finally:
            self.is_executing_input = False  # Re-enable main loop ticking
    
    def tick(self) -> bool:
        """
        Advance the emulation by one frame.
        
        Returns:
            True if emulation is still running, False if stopped
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized")
            return False
            
        try:
            # Check PyBoy state before ticking
            if hasattr(self.pyboy, 'stopped') and self.pyboy.stopped:
                logger.warning("PyBoy reports game has stopped")
                return False
            
            # Advance one frame
            result = self.pyboy.tick()
            
            # Check if game is still running
            if not result:
                logger.warning("Game stopped running - PyBoy tick returned False")
                # Try to get more diagnostic info
                try:
                    if hasattr(self.pyboy, 'stopped'):
                        logger.warning(f"PyBoy stopped flag: {self.pyboy.stopped}")
                    if hasattr(self.pyboy, 'cartridge') and self.pyboy.cartridge:
                        logger.warning("Cartridge still loaded")
                    else:
                        logger.error("Cartridge not loaded - possible ROM issue")
                except Exception as diag_e:
                    logger.debug(f"Could not get diagnostic info: {diag_e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error during tick: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Log full stack trace for debugging
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            
            # Try to get more info about the error
            try:
                if hasattr(self.pyboy, 'stopped'):
                    logger.error(f"PyBoy stopped flag: {self.pyboy.stopped}")
            except:
                pass
            return False
    
    def check_health(self) -> dict:
        """
        Check PyBoy and game health status.
        
        Returns:
            Dictionary with health status information
        """
        if not self.pyboy:
            return {'healthy': False, 'reason': 'PyBoy not initialized'}
        
        try:
            health_info = {
                'healthy': True,
                'pyboy_stopped': False,
                'cartridge_loaded': False,
                'errors': []
            }
            
            # Check if PyBoy reports stopped
            if hasattr(self.pyboy, 'stopped'):
                health_info['pyboy_stopped'] = self.pyboy.stopped
                if self.pyboy.stopped:
                    health_info['healthy'] = False
                    health_info['errors'].append('PyBoy reports stopped')
            
            # Check cartridge status
            if hasattr(self.pyboy, 'cartridge'):
                health_info['cartridge_loaded'] = self.pyboy.cartridge is not None
                if not health_info['cartridge_loaded']:
                    health_info['healthy'] = False
                    health_info['errors'].append('Cartridge not loaded')
            
            return health_info
            
        except Exception as e:
            return {
                'healthy': False,
                'reason': f'Health check failed: {e}',
                'error_type': type(e).__name__
            }
    
    def read_memory(self, address: int) -> int:
        """
        Read a byte from Game Boy memory.
        
        Args:
            address: Memory address to read from (0x0000-0xFFFF)
            
        Returns:
            Byte value at the address (0-255)
        """
        if not self.pyboy:
            return 0
        
        try:
            return self.pyboy.get_memory_value(address)
        except Exception as e:
            logger.debug(f"Failed to read memory at 0x{address:04X}: {e}")
            return 0
    
    def get_game_state(self) -> dict:
        """
        Extract game state information including player position.
        
        Returns:
            Dictionary containing game state data
        """
        if not self.pyboy:
            return {}
            
        try:
            # Detect if we're in a text box by checking screen patterns
            is_in_text_box = self._detect_text_box()
            
            # Extract text from screen
            screen_image = self.get_screen_image()
            detected_text = ""
            if screen_image is not None:
                detected_text = self.text_extractor.extract_text_from_screen(screen_image) or ""
            
            # Read player position from memory
            # Common memory addresses for Link's Awakening (may need adjustment):
            # Player X position is typically around 0xD100-0xD102
            # Player Y position is typically around 0xD101-0xD103
            # Room/screen ID is typically around 0xD700
            
            # Try common memory addresses for Link's Awakening
            position_x = self.read_memory(0xD100)  # Player X coordinate
            position_y = self.read_memory(0xD101)  # Player Y coordinate
            room_id = self.read_memory(0xD700)     # Current room/screen ID
            
            # Read Link's facing direction (common address for Link's Awakening)
            # Typical values: 0=down, 1=up, 2=left, 3=right
            direction_value = self.read_memory(0xD005)  # Link's direction
            direction_map = {0: 'down', 1: 'up', 2: 'left', 3: 'right'}
            facing_direction = direction_map.get(direction_value, 'unknown')
            
            # Alternative addresses if the above don't work:
            # position_x = self.read_memory(0xD202)
            # position_y = self.read_memory(0xD203)
            # direction = self.read_memory(0xD027) or 0xD006
            
            return {
                'health': self.read_memory(0xDB5A),  # Player health (common address)
                'rupees': 0,  # Read from memory (address TBD)
                'current_screen': room_id,
                'position_x': position_x,
                'position_y': position_y,
                'room_id': room_id,
                'facing_direction': facing_direction,
                'in_text_box': is_in_text_box,
                'in_menu': False,
                'in_cutscene': False,
                'text_detected': detected_text,
                'text_history': self.text_extractor.get_text_history(),
            }
        except Exception as e:
            logger.error(f"Failed to read game state: {e}")
            return {}
    
    def _detect_text_box(self) -> bool:
        """
        Detect if Link is currently in a text box/dialogue.
        
        Returns:
            True if in text box, False otherwise
        """
        try:
            # Get current screen
            screen_image = self.pyboy.screen.image
            screen_array = np.array(screen_image)
            
            # Check for text box patterns (black borders, text areas)
            # This is a simple heuristic - you might need to refine based on actual Zelda patterns
            
            # Check bottom area for text box (common in Zelda games)
            height, width = screen_array.shape[:2]
            bottom_area = screen_array[int(height * 0.7):, :]
            
            # Look for dark/black areas that might indicate text boxes
            dark_pixels = np.sum(bottom_area < 50, axis=2)  # Count dark pixels
            dark_ratio = np.sum(dark_pixels > 2) / dark_pixels.size  # Ratio of dark areas
            
            # If there's a significant dark area in the bottom, likely a text box
            is_text_box = dark_ratio > 0.3
            
            if is_text_box:
                logger.info("📝 Text box detected - should press A to advance")
            
            return is_text_box
            
        except Exception as e:
            logger.error(f"Failed to detect text box: {e}")
            return False
    
    def save_state(self) -> bool:
        """
        Save the current game state to a file.
        
        Returns:
            True if save successful, False otherwise
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized, cannot save state")
            return False
        
        try:
            # PyBoy save state
            with open(self.save_state_file, "wb") as f:
                self.pyboy.save_state(f)
            logger.info(f"💾 Game state saved to {self.save_state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save game state: {e}")
            return False
    
    def load_state(self) -> bool:
        """
        Load a previously saved game state.
        
        Returns:
            True if load successful, False otherwise
        """
        if not self.pyboy:
            logger.error("PyBoy not initialized, cannot load state")
            return False
        
        if not os.path.exists(self.save_state_file):
            logger.info("No save state file found")
            return False
        
        try:
            # PyBoy load state
            with open(self.save_state_file, "rb") as f:
                self.pyboy.load_state(f)
            logger.info(f"📂 Game state loaded from {self.save_state_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load game state: {e}")
            return False
    
    def close(self):
        """Close PyBoy emulation."""
        if self.pyboy:
            try:
                # Save state before closing
                self.save_state()
                self.pyboy.stop()
                logger.info("PyBoy closed successfully")
            except Exception as e:
                logger.error(f"Error closing PyBoy: {e}")
            finally:
                self.pyboy = None
