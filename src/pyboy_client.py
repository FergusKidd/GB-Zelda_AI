"""
PyBoy integration for running Zelda ROM and capturing screen data.
"""
import os
import logging
from typing import Optional, Tuple
import numpy as np
from PIL import Image
from pyboy import PyBoy
from pyboy.utils import WindowEvent

logger = logging.getLogger(__name__)


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
        self.pyboy: Optional[PyBoy] = None
        self.screen_width = 160
        self.screen_height = 144
        
    def initialize(self) -> bool:
        """
        Initialize PyBoy with the ROM.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not os.path.exists(self.rom_path):
                logger.error(f"ROM file not found: {self.rom_path}")
                return False
                
            self.pyboy = PyBoy(self.rom_path, window=self.window_type)
            self.pyboy.set_emulation_speed(self.game_speed)
            
            # Skip initial boot sequence
            for _ in range(60):  # Wait for boot
                self.pyboy.tick()
                
            logger.info(f"PyBoy initialized successfully with ROM: {self.rom_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PyBoy: {e}")
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
            logger.info(f"🔘 Sending button press: {button} (delay: {delay} frames)")
            self.pyboy.send_input(button_map[button], delay=delay)
            logger.info(f"✅ Button press sent successfully: {button}")
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
            for i, action in enumerate(sequence):
                button = action['button']
                duration_frames = action['duration']
                delay_frames = action.get('delay', 0)
                
                logger.info(f"🎮 Action {i+1}/{len(sequence)}: {button.upper()} for {duration_frames} frames")
                
                # Use PyBoy's delay parameter for precise timing
                if not self.press_button(button, delay=duration_frames):
                    logger.error(f"Failed to execute action: {action}")
                    return False
                
                # Wait for delay between actions
                if delay_frames > 0:
                    logger.info(f"⏱️  Waiting {delay_frames} frames between actions")
                    for _ in range(delay_frames):
                        self.pyboy.tick()
            
            # Ensure all inputs are fully processed
            logger.info("🔄 Processing final inputs...")
            for _ in range(5):  # Extra ticks to ensure processing
                self.pyboy.tick()
            
            logger.info(f"✅ Sequence completed: {len(sequence)} actions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute sequence: {e}")
            return False
    
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
            return self.pyboy.tick()
        except Exception as e:
            logger.error(f"Failed to tick PyBoy: {e}")
            return False
    
    def get_game_state(self) -> dict:
        """
        Extract basic game state information including text box detection.
        
        Returns:
            Dictionary containing game state data
        """
        if not self.pyboy:
            return {}
            
        try:
            # Detect if we're in a text box by checking screen patterns
            is_in_text_box = self._detect_text_box()
            
            # This is a placeholder - you'll need to implement actual game state reading
            # based on memory addresses specific to Zelda
            return {
                'health': 0,  # Read from memory
                'rupees': 0,  # Read from memory
                'current_screen': 0,  # Read from memory
                'position_x': 0,  # Read from memory
                'position_y': 0,  # Read from memory
                'in_text_box': is_in_text_box,  # Detect dialogue/text
                'in_menu': False,  # Detect menu state
                'in_cutscene': False,  # Detect cutscene
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
    
    def close(self):
        """Close PyBoy emulation."""
        if self.pyboy:
            try:
                self.pyboy.stop()
                logger.info("PyBoy closed successfully")
            except Exception as e:
                logger.error(f"Error closing PyBoy: {e}")
            finally:
                self.pyboy = None
