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
    
    def get_high_level_plan(self, screen_image: np.ndarray, game_state: Dict[str, Any], history_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Get a high-level plan from the AI (strategic goals).
        
        Args:
            screen_image: Current screen as numpy array
            game_state: Current game state
            history_context: History context for planning
            
        Returns:
            Dictionary with high-level plan
        """
        try:
            # Encode screen image
            image_base64 = self.encode_image(screen_image)
            
            # Create planning prompt
            prompt = self._create_planning_prompt(game_state, history_context)
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strategic game planner for The Legend of Zelda. Create high-level goals and plans."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # Parse the response
            plan_text = response.choices[0].message.content
            plan = self._parse_plan(plan_text)
            
            logger.debug(f"Received planning decision: {plan}")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to get planning decision from Azure OpenAI: {e}")
            return None
    
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
        # Get current position for context
        
        current_x = game_state.get('position_x', 0)
        current_y = game_state.get('position_y', 0)
        current_room = game_state.get('room_id', 0)
        facing_direction = game_state.get('facing_direction', 'unknown')
        is_stuck = game_state.get('is_stuck', False)
        
        stuck_warning = ""
        if is_stuck:
            stuck_warning = "\n🚨 STUCK WARNING: You have been in the same position for 5 decisions. Try a DIFFERENT direction or action!\n"
        
        # Get current plan
        current_plan_text = ""
        if history_context and history_context.get('current_plan'):
            plan = history_context['current_plan']
            current_plan_text = f"""
📋 CURRENT PLAN (work towards this goal):
Goal: {plan['goal']}
Steps: {', '.join(plan['steps'])}
"""
        
        # Get room visit information
        room_info = game_state.get('room_info', {})
        is_new_room = room_info.get('is_new', False)
        visit_count = room_info.get('visit_count', 1)
        total_rooms = room_info.get('total_rooms_visited', 1)
        
        room_status = ""
        if is_new_room:
            room_status = f"\n🆕 THIS IS A NEW ROOM! (Total rooms explored: {total_rooms})"
        else:
            room_status = f"\n🔄 You have been in this room before (visit #{visit_count})"
        
        prompt = f"""
You are playing The Legend of Zelda on Game Boy. Look at the current screen and decide what Link should do next.

Your Current Position:
- Room ID: {current_room}
- Coordinates: X={current_x}, Y={current_y}
- Facing Direction: {facing_direction.upper()}
- In Text Box: {game_state.get('in_text_box', False)}
- Text Detected: "{game_state.get('text_detected', '')}"
{room_status}
{stuck_warning}
{current_plan_text}
{self._format_history_context(history_context, current_room)}

CRITICAL RULES:
1. If "In Text Box" is True: ONLY press 'a' to advance dialogue
2. If you see text/dialogue: Press 'a' to continue
3. You must be facing an NPC to interact with them - check your facing direction
4. Try to talk to NPCs at least once, but do not repeatedly talk to the same NPC over and over
5. If you see a STUCK WARNING, try completely different movements (opposite direction, different room exit)
6. If this is a NEW ROOM: Explore carefully and look for NPCs, items, and exits
7. If you've been here BEFORE: Move through quickly unless you have a specific goal here
8. Prioritize exploring NEW rooms over revisiting old ones

Available Actions:
- up, down, left, right: Move Link
- a: Interact, attack, advance dialogue
- b: Use item, cancel

IMPORTANT: 
- Look carefully at the screen image. If you see ANY text, dialogue, or words on screen, include them in the "screen_text" field.
- Create a sequence of 2-3 button presses for efficient movement and interaction
- Use short durations (5-15 frames per button)

Examples:
- Advance dialogue: [{{"button": "a", "duration": 5, "delay": 0}}]
- Move right multiple times: [{{"button": "right", "duration": 15, "delay": 2}}, {{"button": "right", "duration": 15, "delay": 0}}]
- Move and interact: [{{"button": "down", "duration": 15, "delay": 2}}, {{"button": "a", "duration": 5, "delay": 0}}]
- Explore efficiently: [{{"button": "up", "duration": 15, "delay": 2}}, {{"button": "right", "duration": 15, "delay": 2}}, {{"button": "down", "duration": 15, "delay": 0}}]

Respond with JSON only (sequence should have 2-3 actions for efficient gameplay):
{{
  "sequence": [
    {{"button": "right", "duration": 15, "delay": 2}},
    {{"button": "right", "duration": 15, "delay": 0}}
  ],
  "reasoning": "Brief explanation of why these actions",
  "confidence": 0.9,
  "goals": ["Goal 1", "Goal 2"],
  "screen_text": "Any text you see on screen, or empty string if none"
}}
"""
        return prompt
    
    def _create_planning_prompt(self, game_state: Dict[str, Any], history_context: Dict[str, Any] = None) -> str:
        """
        Create prompt for high-level planning AI.
        
        Args:
            game_state: Current game state
            history_context: History context
            
        Returns:
            Planning prompt string
        """
        current_room = game_state.get('room_id', 0)
        current_x = game_state.get('position_x', 0)
        current_y = game_state.get('position_y', 0)
        
        # Get room exploration info
        room_info = game_state.get('room_info', {})
        is_new_room = room_info.get('is_new', False)
        total_rooms = room_info.get('total_rooms_visited', 1)
        
        exploration_status = f"\nExploration Progress: {total_rooms} rooms discovered"
        if is_new_room:
            exploration_status += " (This is a NEW room!)"
        
        # Get recent story for context
        recent_story = []
        if history_context:
            story_events = history_context.get('recent_story', [])
            recent_story = [event.get('content', '')[:60] for event in story_events[-5:] if event.get('type') == 'dialogue']
        
        story_context = ""
        if recent_story:
            story_context = "\nRecent Dialogue:\n" + "\n".join([f"  - {s}..." for s in recent_story])
        
        prompt = f"""
You are a strategic planner for The Legend of Zelda game. Look at the current screen and story progress to create a high-level goal.

Current Status:
- Room: {current_room}
- Position: X={current_x}, Y={current_y}
{exploration_status}
{story_context}

Your Task:
1. Look carefully at the screen and describe what you see (NPCs, objects, environment)
2. Create a clear, achievable goal for Link based on what you see and the story so far
3. Be DESCRIPTIVE about characters - mention their appearance, clothing, or distinctive features

Examples of good goals:
- "Find and talk to the old bearded man in the red robe standing in this house"
- "Exit the house through the door at the bottom and explore the village outside"
- "Go upstairs to look for treasure chests or items in the upper room"
- "Talk to the shopkeeper behind the counter to see what's for sale"
- "Approach and talk to the young woman in the green dress near the fireplace"
- "Explore the dark cave entrance to the north of the village"

IMPORTANT: Be descriptive about NPCs! Mention what they look like, what they're wearing, where they are positioned.

Respond with JSON only:
{{
  "goal": "Clear descriptive goal mentioning character details",
  "steps": ["Describe what to do in each step", "Be specific about locations and characters", "Include visual details"],
  "reasoning": "Why this goal makes sense based on what you see on screen and the story"
}}
"""
        return prompt
    
    def _format_history_context(self, history_context: Dict[str, Any], current_room: int) -> str:
        """
        Format history context for the AI prompt, filtered by current room.
        
        Args:
            history_context: History context from HistoryManager
            current_room: Current room ID to filter NPCs
            
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
        
        # Show NPCs in CURRENT ROOM that have been talked to
        npc_interactions = history_context.get('npc_interactions', {})
        repeated = npc_interactions.get('repeated_interactions', [])
        
        # Filter to only show NPCs in the current room
        current_room_npcs = [npc for npc in repeated if npc['position']['room'] == current_room]
        
        if current_room_npcs:
            context_parts.append("\n⚠️  NPCs ALREADY TALKED TO IN THIS ROOM (DO NOT talk to them again):")
            for npc in current_room_npcs:
                pos = npc['position']
                context_parts.append(f"  - At coordinates X={pos['x']}, Y={pos['y']}: \"{npc['dialogue_snippet'][:40]}...\" (talked {npc['count']}x)")
        
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
    
    def _parse_plan(self, plan_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the planning AI response.
        
        Args:
            plan_text: Raw text response from planning AI
            
        Returns:
            Parsed plan dictionary or None if parsing fails
        """
        try:
            # Remove markdown code blocks if present
            plan_text = plan_text.strip()
            if plan_text.startswith('```json'):
                plan_text = plan_text[7:-3]
            elif plan_text.startswith('```'):
                plan_text = plan_text[3:-3]
            
            # Parse JSON
            plan = json.loads(plan_text)
            
            # Validate required fields
            required_fields = ['goal', 'steps', 'reasoning']
            for field in required_fields:
                if field not in plan:
                    logger.error(f"Missing required field in plan: {field}")
                    return None
            
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
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
