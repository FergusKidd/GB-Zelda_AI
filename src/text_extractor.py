"""
Text extraction from game screens using OCR.
"""
import cv2
import numpy as np
import logging
from typing import Optional, List, Dict, Any
from PIL import Image

# Try to import pytesseract, but don't fail if not available
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not available - text extraction will be disabled")

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extracts text from game screens using OCR."""
    
    def __init__(self):
        """Initialize text extractor."""
        self.last_text = ""
        self.text_history: List[str] = []
        
        # Configure tesseract for Game Boy text (simplified config to avoid parsing errors)
        self.tesseract_config = '--psm 8'
        
        logger.info("Text extractor initialized")
    
    def extract_text_from_screen(self, screen_image: np.ndarray) -> Optional[str]:
        """
        Extract text from a game screen image.
        
        Args:
            screen_image: Screen image as numpy array
            
        Returns:
            Extracted text or None if no text found
        """
        try:
            # Check if Tesseract is available
            if not TESSERACT_AVAILABLE:
                logger.debug("Tesseract not available, skipping text extraction")
                return None
            
            # Convert to PIL Image
            if len(screen_image.shape) == 3:
                pil_image = Image.fromarray(screen_image)
            else:
                pil_image = Image.fromarray(screen_image)
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_for_ocr(pil_image)
            
            # Extract text using OCR
            try:
                text = pytesseract.image_to_string(processed_image, config=self.tesseract_config)
            except Exception as ocr_error:
                logger.debug(f"OCR failed: {ocr_error}")
                return None
            
            # Clean up the text
            cleaned_text = self._clean_text(text)
            
            if cleaned_text and cleaned_text != self.last_text:
                logger.info(f"📝 Text detected: {cleaned_text}")
                self.last_text = cleaned_text
                self.text_history.append(cleaned_text)
                
                # Keep only last 10 text detections
                if len(self.text_history) > 10:
                    self.text_history.pop(0)
                
                return cleaned_text
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            return None
    
    def _preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to numpy array for processing
            img_array = np.array(image)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Increase contrast
            gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
            
            # Morphological operations to clean up text
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(binary)
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Failed to preprocess image: {e}")
            return image
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        cleaned = ' '.join(text.split())
        
        # Remove very short strings (likely OCR errors)
        if len(cleaned) < 3:
            return ""
        
        # Remove common OCR artifacts
        artifacts = ['|', ']', '[', '}', '{', '~', '`']
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')
        
        return cleaned.strip()
    
    def get_text_history(self) -> List[str]:
        """Get history of detected text."""
        return self.text_history.copy()
    
    def get_last_text(self) -> str:
        """Get the last detected text."""
        return self.last_text
    
    def detect_text_box_region(self, screen_image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect and extract text box region from screen.
        
        Args:
            screen_image: Full screen image
            
        Returns:
            Text box region as numpy array or None
        """
        try:
            height, width = screen_image.shape[:2]
            
            # Focus on bottom area where text boxes typically appear
            bottom_region = screen_image[int(height * 0.6):, :]
            
            # Convert to grayscale for analysis
            if len(bottom_region.shape) == 3:
                gray = cv2.cvtColor(bottom_region, cv2.COLOR_RGB2GRAY)
            else:
                gray = bottom_region
            
            # Find contours that might be text boxes
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for rectangular contours (text boxes)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check if this looks like a text box
                aspect_ratio = w / h
                area = w * h
                
                if (aspect_ratio > 2.0 and aspect_ratio < 6.0 and 
                    area > (width * height * 0.1)):  # At least 10% of screen
                    
                    # Extract the text box region
                    text_box = bottom_region[y:y+h, x:x+w]
                    logger.debug(f"Text box region detected: {w}x{h} at ({x}, {y})")
                    return text_box
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect text box region: {e}")
            return None
