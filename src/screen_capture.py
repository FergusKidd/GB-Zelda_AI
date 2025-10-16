"""
Screen capture and image processing utilities for game analysis.
"""
import logging
import numpy as np
from typing import Optional, Tuple, List
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Handles screen capture and image processing for game analysis."""
    
    def __init__(self, target_size: Tuple[int, int] = (320, 288)):
        """
        Initialize screen capture.
        
        Args:
            target_size: Target size for processed images (width, height)
        """
        self.target_size = target_size
        self.previous_frame: Optional[np.ndarray] = None
        self.frame_history: List[np.ndarray] = []
        self.max_history = 5
        
    def process_frame(self, raw_frame: np.ndarray) -> np.ndarray:
        """
        Process raw frame for better analysis.
        
        Args:
            raw_frame: Raw screen capture from PyBoy
            
        Returns:
            Processed frame optimized for AI analysis
        """
        try:
            # Ensure the frame is in the correct format
            if len(raw_frame.shape) == 2:
                # Grayscale to RGB
                processed_frame = np.stack([raw_frame] * 3, axis=-1)
            else:
                processed_frame = raw_frame.copy()
            
            # Resize to target size
            processed_frame = cv2.resize(processed_frame, self.target_size)
            
            # Enhance contrast for better visibility
            processed_frame = self._enhance_contrast(processed_frame)
            
            # Store in history
            self._update_history(processed_frame)
            
            return processed_frame
            
        except Exception as e:
            logger.error(f"Failed to process frame: {e}")
            return raw_frame
    
    def _enhance_contrast(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance contrast of the frame for better AI analysis.
        
        Args:
            frame: Input frame
            
        Returns:
            Enhanced frame
        """
        try:
            # Convert to LAB color space for better contrast enhancement
            lab = cv2.cvtColor(frame, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Merge channels back
            enhanced_lab = cv2.merge([l, a, b])
            enhanced_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
            
            return enhanced_frame
            
        except Exception as e:
            logger.error(f"Failed to enhance contrast: {e}")
            return frame
    
    def _update_history(self, frame: np.ndarray):
        """Update frame history for motion detection."""
        self.previous_frame = self.frame_history[-1] if self.frame_history else None
        self.frame_history.append(frame)
        
        # Keep only recent frames
        if len(self.frame_history) > self.max_history:
            self.frame_history.pop(0)
    
    def detect_motion(self) -> float:
        """
        Detect motion between current and previous frame.
        
        Returns:
            Motion score (0.0 to 1.0)
        """
        if len(self.frame_history) < 2:
            return 0.0
            
        try:
            current_frame = self.frame_history[-1]
            previous_frame = self.frame_history[-2]
            
            # Convert to grayscale for motion detection
            current_gray = cv2.cvtColor(current_frame, cv2.COLOR_RGB2GRAY)
            previous_gray = cv2.cvtColor(previous_frame, cv2.COLOR_RGB2GRAY)
            
            # Calculate absolute difference
            diff = cv2.absdiff(current_gray, previous_gray)
            
            # Calculate motion score
            motion_score = np.mean(diff) / 255.0
            
            return motion_score
            
        except Exception as e:
            logger.error(f"Failed to detect motion: {e}")
            return 0.0
    
    def extract_game_elements(self, frame: np.ndarray) -> dict:
        """
        Extract game elements from the frame for analysis.
        
        Args:
            frame: Processed game frame
            
        Returns:
            Dictionary containing detected game elements
        """
        try:
            elements = {
                'enemies': self._detect_enemies(frame),
                'items': self._detect_items(frame),
                'walls': self._detect_walls(frame),
                'doors': self._detect_doors(frame),
                'link_position': self._detect_link(frame)
            }
            
            return elements
            
        except Exception as e:
            logger.error(f"Failed to extract game elements: {e}")
            return {}
    
    def _detect_enemies(self, frame: np.ndarray) -> List[dict]:
        """
        Detect enemies in the frame.
        
        Args:
            frame: Game frame
            
        Returns:
            List of enemy positions and types
        """
        # This is a placeholder implementation
        # In a real implementation, you would use computer vision techniques
        # like template matching, color detection, or machine learning models
        
        enemies = []
        
        # Example: Simple color-based detection for red enemies
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            
            # Define range for red color (enemies)
            lower_red = np.array([0, 50, 50])
            upper_red = np.array([10, 255, 255])
            
            # Create mask
            mask = cv2.inRange(hsv, lower_red, upper_red)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 50:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    enemies.append({
                        'position': (x + w//2, y + h//2),
                        'size': (w, h),
                        'type': 'enemy'
                    })
                    
        except Exception as e:
            logger.error(f"Failed to detect enemies: {e}")
        
        return enemies
    
    def _detect_items(self, frame: np.ndarray) -> List[dict]:
        """
        Detect items in the frame.
        
        Args:
            frame: Game frame
            
        Returns:
            List of item positions and types
        """
        # Placeholder implementation
        items = []
        
        try:
            # Example: Detect yellow items (rupees, keys, etc.)
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            
            # Define range for yellow color
            lower_yellow = np.array([20, 50, 50])
            upper_yellow = np.array([30, 255, 255])
            
            mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 20:  # Smaller threshold for items
                    x, y, w, h = cv2.boundingRect(contour)
                    items.append({
                        'position': (x + w//2, y + h//2),
                        'size': (w, h),
                        'type': 'item'
                    })
                    
        except Exception as e:
            logger.error(f"Failed to detect items: {e}")
        
        return items
    
    def _detect_walls(self, frame: np.ndarray) -> List[dict]:
        """
        Detect walls and obstacles.
        
        Args:
            frame: Game frame
            
        Returns:
            List of wall positions
        """
        # Placeholder implementation
        walls = []
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Find lines (walls)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    walls.append({
                        'start': (x1, y1),
                        'end': (x2, y2),
                        'type': 'wall'
                    })
                    
        except Exception as e:
            logger.error(f"Failed to detect walls: {e}")
        
        return walls
    
    def _detect_doors(self, frame: np.ndarray) -> List[dict]:
        """
        Detect doors and passages.
        
        Args:
            frame: Game frame
            
        Returns:
            List of door positions
        """
        # Placeholder implementation
        doors = []
        
        try:
            # Look for rectangular shapes that could be doors
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            
            # Detect rectangles
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Approximate contour to polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Check if it's roughly rectangular
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h
                    
                    # Doors typically have specific aspect ratios
                    if 0.3 < aspect_ratio < 3.0 and w > 20 and h > 20:
                        doors.append({
                            'position': (x + w//2, y + h//2),
                            'size': (w, h),
                            'type': 'door'
                        })
                        
        except Exception as e:
            logger.error(f"Failed to detect doors: {e}")
        
        return doors
    
    def _detect_link(self, frame: np.ndarray) -> Optional[dict]:
        """
        Detect Link's position in the frame.
        
        Args:
            frame: Game frame
            
        Returns:
            Link's position and state or None if not found
        """
        # Placeholder implementation
        try:
            # Look for Link's characteristic colors (green tunic)
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            
            # Define range for green color (Link's tunic)
            lower_green = np.array([40, 50, 50])
            upper_green = np.array([80, 255, 255])
            
            mask = cv2.inRange(hsv, lower_green, upper_green)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest green contour (likely Link)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                
                if area > 100:  # Minimum area for Link
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    return {
                        'position': (x + w//2, y + h//2),
                        'size': (w, h),
                        'type': 'link'
                    }
                    
        except Exception as e:
            logger.error(f"Failed to detect Link: {e}")
        
        return None
    
    def save_frame(self, frame: np.ndarray, filename: str):
        """
        Save frame to file for debugging.
        
        Args:
            frame: Frame to save
            filename: Output filename
        """
        try:
            image = Image.fromarray(frame.astype(np.uint8))
            image.save(filename)
            logger.info(f"Frame saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
