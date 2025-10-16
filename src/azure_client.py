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
    
    def get_game_decision(self, screen_image: np.ndarray, game_state: Dict[str, Any], history_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Send screen capture to Azure OpenAI and get game decision.
        
        Args:
            screen_image: Current screen as numpy array
            game_state: Current game state information
            history_context: History context for better decision making
            
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
            prompt = self._create_game_prompt(game_state, history_context)
            
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
            
            logger.debug(f"Received AI decision: {decision}")
            return decision
            
        except Exception as e:
            logger.error(f"Failed to get game decision from Azure OpenAI: {e}")
            return None
    
    def _create_game_prompt(self, game_state: Dict[str, Any], history_context: Dict[str, Any] = None) -> str:
        """
        Create the prompt for the AI based on current game state.
        
        Args:
            game_state: Current game state information
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
You are playing The Legend of Zelda on Game Boy. Look at the current screen and decide what Link should do next.

Current Situation:
- In Text Box: {game_state.get('in_text_box', False)}
- Text Detected: "{game_state.get('text_detected', '')}"

{self._format_history_context(history_context)}

CRITICAL RULES:
1. If "In Text Box" is True: ONLY press 'a' to advance dialogue
2. If you see text/dialogue: Press 'a' to continue
3. Otherwise: Move Link to explore and find items/NPCs
4. You must be facing an NPC directly before pressing 'a' to interact with them
5. Do not repeatedly talk to the same NPC over and over

Available Actions:
- up, down, left, right: Move Link
- a: Interact, attack, advance dialogue
- b: Use item, cancel

IMPORTANT: Look carefully at the screen image. If you see ANY text, dialogue, or words on screen, include them in the "screen_text" field.

Create a simple sequence of 1-3 button presses. Use short durations (5-15 frames).

Examples:
- Advance dialogue: [{{"button": "a", "duration": 5, "delay": 0}}]
- Move and interact: [{{"button": "right", "duration": 15, "delay": 2}}, {{"button": "a", "duration": 5, "delay": 0}}]

Respond with JSON only:
{{
  "sequence": [{{"button": "a", "duration": 5, "delay": 0}}],
  "reasoning": "Brief explanation",
  "confidence": 0.9,
  "goals": ["Goal 1", "Goal 2"],
  "screen_text": "Any text you see on screen, or empty string if none"
}}
"""
        return prompt
    
    def _format_history_context(self, history_context: Dict[str, Any]) -> str:
        """
        Format history context for the AI prompt (simplified to avoid confusion).
        
        Args:
            history_context: History context from HistoryManager
            
        Returns:
            Formatted history context string
        """
        if not history_context:
            return ""
        
        context_parts = []
        
        # Only show the last 2 decisions to avoid overwhelming the AI
        recent_decisions = history_context.get('recent_decisions', [])
        if recent_decisions:
            context_parts.append("Recent Actions:")
            for decision in recent_decisions[-2:]:  # Only last 2 decisions
                sequence_str = ", ".join([action['button'] for action in decision['sequence']])
                success_str = "✅" if decision['success'] else "❌"
                context_parts.append(f"  {success_str} {sequence_str}")
        
        # Only show recent story events if they're dialogue
        recent_story = history_context.get('recent_story', [])
        if recent_story:
            dialogue_events = [event for event in recent_story[-3:] if event['type'] == 'dialogue']
            if dialogue_events:
                context_parts.append("\nRecent Dialogue:")
                for event in dialogue_events:
                    context_parts.append(f"  \"{event['content'][:50]}...\"")
        
        if context_parts:
            return "\n".join(context_parts) + "\n"
        return ""
    
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
            
            # Add default screen_text if not provided
            if 'screen_text' not in decision:
                decision['screen_text'] = ""
            
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
