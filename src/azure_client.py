"""
Azure OpenAI client for sending screen captures and receiving game decisions.
"""
import os
import base64
import logging
from typing import Optional, Dict, Any
import json
from io import BytesIO
import numpy as np
from PIL import Image
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Client for communicating with Azure OpenAI for game decision making."""
    
    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment_name: str):
        """
        Initialize Azure OpenAI client.
        
        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            api_version: API version to use
            deployment_name: Deployment name for the model
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.deployment_name = deployment_name
        
        # Initialize the client
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        logger.info(f"Azure OpenAI client initialized with deployment: {deployment_name}")
    
    def encode_image(self, image_array: np.ndarray) -> str:
        """
        Encode numpy array image to base64 string.
        
        Args:
            image_array: Image as numpy array (RGB format)
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Convert numpy array to PIL Image
            if len(image_array.shape) == 3:
                image = Image.fromarray(image_array.astype(np.uint8))
            else:
                image = Image.fromarray(image_array.astype(np.uint8), mode='L')
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to manageable size for API (optional)
            image = image.resize((320, 288))  # 2x scale of original 160x144
            
            # Encode to base64
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            
            return base64.b64encode(image_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return ""
    
    def get_game_decision(self, screen_image: np.ndarray, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send screen capture to Azure OpenAI and get game decision.
        
        Args:
            screen_image: Current screen as numpy array
            game_state: Current game state information
            
        Returns:
            Dictionary containing AI decision or None if failed
        """
        try:
            # Encode the image
            image_base64 = self.encode_image(screen_image)
            if not image_base64:
                logger.error("Failed to encode screen image")
                return None
            
            # Prepare the prompt
            prompt = self._create_game_prompt(game_state)
            
            # Create the message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            # Parse the response
            decision_text = response.choices[0].message.content
            decision = self._parse_decision(decision_text)
            
            logger.info(f"Received AI decision: {decision}")
            return decision
            
        except Exception as e:
            logger.error(f"Failed to get game decision from Azure OpenAI: {e}")
            return None
    
    def _create_game_prompt(self, game_state: Dict[str, Any]) -> str:
        """
        Create the prompt for the AI based on current game state.
        
        Args:
            game_state: Current game state information
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
You are playing The Legend of Zelda on Game Boy. Analyze the current screen and create a sequence of button presses to achieve your goals.

Current Game State:
- Health: {game_state.get('health', 'Unknown')}
- Rupees: {game_state.get('rupees', 'Unknown')}
- Current Screen: {game_state.get('current_screen', 'Unknown')}
- Position: ({game_state.get('position_x', 'Unknown')}, {game_state.get('position_y', 'Unknown')})
- In Text Box: {game_state.get('in_text_box', False)}
- In Menu: {game_state.get('in_menu', False)}

IMPORTANT: If "In Text Box" is True, you MUST press 'a' to advance the dialogue. Do NOT try to move or do other actions.

Available Game Boy Buttons:
- up, down, left, right: Move Link
- a: Sword attack, interact with objects/NPCs
- b: Use equipped item, cancel
- start: Open pause menu
- select: Open item menu

Create a sequence of button presses (2-5 actions) to accomplish your immediate goals. Each action should specify:
- button: The button to press
- duration: How long to hold it (in frames, 60fps = 1 second)
- delay: Wait time after releasing (in frames)

Analyze the screen carefully and respond with a JSON object containing:
1. "sequence": Array of button actions [{{"button": "right", "duration": 30, "delay": 10}}, ...]
2. "reasoning": Brief explanation of the strategy
3. "confidence": Confidence level from 0.0 to 1.0
4. "goals": List of 2-3 immediate goals you're trying to achieve

Focus on:
- Avoiding enemies and obstacles
- Collecting items and rupees
- Progressing through the game
- Maintaining health
- Exploring new areas
- ADVANCING DIALOGUE when in text boxes

CRITICAL RULES:
1. If "In Text Box" is True: ONLY press 'a' to advance dialogue
2. If "In Menu" is True: Use appropriate menu navigation
3. Never try to move when in dialogue or menus

Example sequences:
- Move right and attack: [{{"button": "right", "duration": 30, "delay": 5}}, {{"button": "a", "duration": 10, "delay": 0}}]
- Explore area: [{{"button": "up", "duration": 20, "delay": 5}}, {{"button": "right", "duration": 25, "delay": 5}}]

Note: Use shorter durations (15-30 frames) for movement buttons for more responsive control.

Respond ONLY with valid JSON, no other text.
"""
        return prompt
    
    def _parse_decision(self, decision_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the AI decision response.
        
        Args:
            decision_text: Raw response text from AI
            
        Returns:
            Parsed decision dictionary or None if parsing failed
        """
        try:
            # Clean the response text
            decision_text = decision_text.strip()
            
            # Try to find JSON in the response
            if decision_text.startswith('```json'):
                decision_text = decision_text[7:-3]
            elif decision_text.startswith('```'):
                decision_text = decision_text[3:-3]
            
            # Parse JSON
            decision = json.loads(decision_text)
            
            # Validate required fields
            required_fields = ['sequence', 'reasoning', 'confidence']
            for field in required_fields:
                if field not in decision:
                    logger.error(f"Missing required field in AI decision: {field}")
                    return None
            
            # Validate sequence
            if not isinstance(decision['sequence'], list) or len(decision['sequence']) == 0:
                logger.error("Invalid sequence: must be non-empty array")
                return None
            
            # Validate each action in sequence
            valid_buttons = ['up', 'down', 'left', 'right', 'a', 'b', 'start', 'select']
            for i, action in enumerate(decision['sequence']):
                if not isinstance(action, dict):
                    logger.error(f"Invalid action {i}: must be object")
                    return None
                
                if 'button' not in action or 'duration' not in action:
                    logger.error(f"Invalid action {i}: missing button or duration")
                    return None
                
                if action['button'] not in valid_buttons:
                    logger.error(f"Invalid button in action {i}: {action['button']}")
                    return None
                
                if not isinstance(action['duration'], (int, float)) or action['duration'] <= 0:
                    logger.error(f"Invalid duration in action {i}: {action['duration']}")
                    return None
                
                # Add default delay if not specified
                if 'delay' not in action:
                    action['delay'] = 0
                elif not isinstance(action['delay'], (int, float)) or action['delay'] < 0:
                    logger.error(f"Invalid delay in action {i}: {action['delay']}")
                    return None
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI decision as JSON: {e}")
            logger.error(f"Raw response: {decision_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing AI decision: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the connection to Azure OpenAI.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Simple test message
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            
            logger.info("Azure OpenAI connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Azure OpenAI connection test failed: {e}")
            return False
