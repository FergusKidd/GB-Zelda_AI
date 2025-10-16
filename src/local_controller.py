"""
Local controller for translating AI decisions into PyBoy button presses.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of possible game actions."""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    PRESS_A = "press_a"
    PRESS_B = "press_b"
    PRESS_START = "press_start"
    PRESS_SELECT = "press_select"
    WAIT = "wait"


class LocalController:
    """Local controller that translates AI decisions into PyBoy button presses."""
    
    def __init__(self, pyboy_client):
        """
        Initialize local controller.
        
        Args:
            pyboy_client: PyBoy client instance for button control
        """
        self.pyboy_client = pyboy_client
        self.action_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Action mapping from AI decisions to PyBoy buttons
        self.action_mapping = {
            ActionType.MOVE_UP: 'up',
            ActionType.MOVE_DOWN: 'down',
            ActionType.MOVE_LEFT: 'left',
            ActionType.MOVE_RIGHT: 'right',
            ActionType.PRESS_A: 'a',
            ActionType.PRESS_B: 'b',
            ActionType.PRESS_START: 'start',
            ActionType.PRESS_SELECT: 'select',
        }
        
        # Timing configuration
        self.button_press_duration = 0.1  # How long to hold buttons
        self.action_cooldown = 0.05  # Minimum time between actions
        
        logger.info("Local controller initialized")
    
    def execute_decision(self, decision: Dict[str, Any]) -> bool:
        """
        Execute an AI decision by translating it to button sequence.
        
        Args:
            decision: AI decision dictionary containing sequence and metadata
            
        Returns:
            True if execution successful, False otherwise
        """
        try:
            sequence = decision.get('sequence', [])
            reasoning = decision.get('reasoning', 'No reasoning provided')
            confidence = decision.get('confidence', 0.0)
            
            logger.debug(f"Executing sequence: {len(sequence)} actions (confidence: {confidence:.2f})")
            logger.debug(f"Reasoning: {reasoning}")
            
            # Validate sequence
            if not sequence:
                logger.error("Empty sequence")
                return False
            
            # Use PyBoy's built-in sequence execution for better timing
            success = self.pyboy_client.execute_sequence(sequence)
            
            # Record action in history
            self._record_action(decision, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute decision: {e}")
            return False
    
    def _execute_sequence(self, sequence: List[Dict[str, Any]]) -> bool:
        """
        Execute a sequence of button actions.
        
        Args:
            sequence: List of button actions with duration and delay
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for i, action in enumerate(sequence):
                button = action['button']
                duration_frames = action['duration']
                delay_frames = action.get('delay', 0)
                
                logger.debug(f"Action {i+1}/{len(sequence)}: {button} for {duration_frames} frames, delay {delay_frames}")
                
                # Press button
                logger.debug(f"🎮 PRESSING BUTTON: {button.upper()}")
                if not self.pyboy_client.press_button(button):
                    logger.error(f"Failed to press button: {button}")
                    return False
                
                # Hold for specified duration (convert frames to seconds)
                # Use shorter, more frequent presses for smoother movement
                if button in ['up', 'down', 'left', 'right']:
                    # Movement buttons: use shorter duration but more responsive
                    hold_time = min(duration_frames / 60.0, 0.3)  # Cap at 0.3 seconds
                    logger.debug(f"⏱️  Holding {button.upper()} for {hold_time:.2f} seconds (optimized for movement)")
                else:
                    # Action buttons: use original duration
                    hold_time = duration_frames / 60.0
                    logger.debug(f"⏱️  Holding {button.upper()} for {hold_time:.2f} seconds")
                
                # Use shorter sleep for more responsive movement
                time.sleep(hold_time)
                
                # Release button
                logger.debug(f"🎮 RELEASING BUTTON: {button.upper()}")
                if not self.pyboy_client.release_button(button):
                    logger.error(f"Failed to release button: {button}")
                    return False
                
                # Wait for delay (convert frames to seconds)
                if delay_frames > 0:
                    delay_time = delay_frames / 60.0  # 60fps
                    time.sleep(min(delay_time, 0.5))  # Cap delay at 0.5 seconds
            
            logger.debug(f"Sequence completed successfully: {len(sequence)} actions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute sequence: {e}")
            return False
    
    def _execute_action(self, action: str) -> bool:
        """
        Execute a specific action.
        
        Args:
            action: Action to execute
            
        Returns:
            True if successful, False otherwise
        """
        try:
            action_type = ActionType(action)
            
            if action_type == ActionType.WAIT:
                # Do nothing
                return True
            
            # Get the corresponding button
            button = self.action_mapping.get(action_type)
            if not button:
                logger.error(f"No button mapping for action: {action}")
                return False
            
            # Press and release the button
            success = self._press_and_release_button(button)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False
    
    def _press_and_release_button(self, button: str) -> bool:
        """
        Press and release a button with proper timing.
        
        Args:
            button: Button to press and release
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Press the button
            if not self.pyboy_client.press_button(button):
                logger.error(f"Failed to press button: {button}")
                return False
            
            # Hold for specified duration
            time.sleep(self.button_press_duration)
            
            # Release the button
            if not self.pyboy_client.release_button(button):
                logger.error(f"Failed to release button: {button}")
                return False
            
            logger.debug(f"Successfully pressed and released button: {button}")
            return True
            
        except Exception as e:
            logger.error(f"Error pressing button {button}: {e}")
            return False
    
    def _record_action(self, decision: Dict[str, Any], success: bool):
        """
        Record action in history for analysis.
        
        Args:
            decision: Original AI decision
            success: Whether execution was successful
        """
        try:
            action_record = {
                'timestamp': time.time(),
                'sequence': decision.get('sequence', []),
                'reasoning': decision.get('reasoning'),
                'confidence': decision.get('confidence'),
                'success': success,
                'goals': decision.get('goals', [])
            }
            
            self.action_history.append(action_record)
            
            # Keep only recent history
            if len(self.action_history) > self.max_history:
                self.action_history.pop(0)
                
        except Exception as e:
            logger.error(f"Failed to record action: {e}")
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recent actions.
        
        Returns:
            Dictionary containing action statistics
        """
        try:
            if not self.action_history:
                return {}
            
            # Count actions by type
            action_counts = {}
            success_counts = {}
            confidence_scores = {}
            
            for record in self.action_history:
                sequence = record.get('sequence', [])
                
                # Count each button press in the sequence
                for action in sequence:
                    button = action.get('button', 'unknown')
                    
                    # Count total actions
                    action_counts[button] = action_counts.get(button, 0) + 1
                    
                    # Count successful actions
                    if record['success']:
                        success_counts[button] = success_counts.get(button, 0) + 1
                    
                    # Track confidence scores
                    if button not in confidence_scores:
                        confidence_scores[button] = []
                    confidence_scores[button].append(record.get('confidence', 0))
            
            # Calculate success rates
            success_rates = {}
            for button in action_counts:
                total = action_counts[button]
                successful = success_counts.get(button, 0)
                success_rates[button] = successful / total if total > 0 else 0
            
            # Calculate average confidence
            avg_confidence = {}
            for button in confidence_scores:
                scores = confidence_scores[button]
                avg_confidence[button] = sum(scores) / len(scores) if scores else 0
            
            return {
                'total_actions': len(self.action_history),
                'action_counts': action_counts,
                'success_rates': success_rates,
                'average_confidence': avg_confidence,
                'recent_actions': self.action_history[-10:] if self.action_history else []
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate action statistics: {e}")
            return {}
    
    def optimize_timing(self) -> Dict[str, float]:
        """
        Analyze action history and suggest timing optimizations.
        
        Returns:
            Dictionary with suggested timing parameters
        """
        try:
            if len(self.action_history) < 10:
                return {}
            
            # Analyze recent actions for timing patterns
            recent_actions = self.action_history[-20:]
            
            # Calculate average success rate
            successful_actions = sum(1 for action in recent_actions if action['success'])
            success_rate = successful_actions / len(recent_actions)
            
            # Suggest timing adjustments based on success rate
            suggestions = {}
            
            if success_rate < 0.7:
                # Low success rate - might need longer button presses
                suggestions['button_press_duration'] = min(0.2, self.button_press_duration * 1.5)
                suggestions['action_cooldown'] = min(0.1, self.action_cooldown * 1.2)
            elif success_rate > 0.9:
                # High success rate - might be able to go faster
                suggestions['button_press_duration'] = max(0.05, self.button_press_duration * 0.8)
                suggestions['action_cooldown'] = max(0.02, self.action_cooldown * 0.8)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to optimize timing: {e}")
            return {}
    
    def apply_timing_optimizations(self, suggestions: Dict[str, float]):
        """
        Apply timing optimizations.
        
        Args:
            suggestions: Dictionary with timing parameter suggestions
        """
        try:
            if 'button_press_duration' in suggestions:
                old_duration = self.button_press_duration
                self.button_press_duration = suggestions['button_press_duration']
                logger.info(f"Updated button press duration: {old_duration:.3f}s -> {self.button_press_duration:.3f}s")
            
            if 'action_cooldown' in suggestions:
                old_cooldown = self.action_cooldown
                self.action_cooldown = suggestions['action_cooldown']
                logger.info(f"Updated action cooldown: {old_cooldown:.3f}s -> {self.action_cooldown:.3f}s")
                
        except Exception as e:
            logger.error(f"Failed to apply timing optimizations: {e}")
    
    def save_action_history(self, filename: str):
        """
        Save action history to file for analysis.
        
        Args:
            filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.action_history, f, indent=2)
            logger.info(f"Action history saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save action history: {e}")
    
    def load_action_history(self, filename: str):
        """
        Load action history from file.
        
        Args:
            filename: Input filename
        """
        try:
            with open(filename, 'r') as f:
                self.action_history = json.load(f)
            logger.info(f"Action history loaded from {filename}")
        except Exception as e:
            logger.error(f"Failed to load action history: {e}")
    
    def reset_history(self):
        """Reset action history."""
        self.action_history = []
        logger.info("Action history reset")
