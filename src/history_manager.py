"""
History manager for tracking AI decisions and game story.
"""
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages decision history and story logs for AI context."""
    
    def __init__(self, max_decisions: int = 10):
        """
        Initialize history manager.
        
        Args:
            max_decisions: Maximum number of recent decisions to keep
        """
        self.max_decisions = max_decisions
        self.decision_history: List[Dict[str, Any]] = []
        self.story_log: List[Dict[str, Any]] = []
        
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        logger.info(f"History manager initialized (max decisions: {max_decisions})")
    
    def add_decision(self, decision: Dict[str, Any], success: bool, game_state: Dict[str, Any]) -> None:
        """
        Add a decision to the history.
        
        Args:
            decision: AI decision that was made
            success: Whether the decision was successful
            game_state: Game state at time of decision
        """
        decision_record = {
            'timestamp': time.time(),
            'decision_id': len(self.decision_history) + 1,
            'sequence': decision.get('sequence', []),
            'reasoning': decision.get('reasoning', ''),
            'confidence': decision.get('confidence', 0.0),
            'goals': decision.get('goals', []),
            'success': success,
            'game_state': game_state.copy(),
            'text_detected': game_state.get('text_detected', ''),
            'in_text_box': game_state.get('in_text_box', False)
        }
        
        self.decision_history.append(decision_record)
        
        # Keep only the most recent decisions
        if len(self.decision_history) > self.max_decisions:
            self.decision_history.pop(0)
        
        logger.debug(f"Added decision #{decision_record['decision_id']} to history")
    
    def add_story_event(self, event_type: str, content: str, context: Dict[str, Any] = None) -> None:
        """
        Add a story event to the log.
        
        Args:
            event_type: Type of event ('dialogue', 'item_found', 'location_change', etc.)
            content: The actual text/content
            context: Additional context about the event
        """
        story_record = {
            'timestamp': time.time(),
            'event_id': len(self.story_log) + 1,
            'type': event_type,
            'content': content,
            'context': context or {}
        }
        
        self.story_log.append(story_record)
        
        logger.info(f"📖 Story event added: {event_type} - {content[:50]}...")
    
    def get_decision_history(self) -> List[Dict[str, Any]]:
        """Get the recent decision history."""
        return self.decision_history.copy()
    
    def get_story_log(self) -> List[Dict[str, Any]]:
        """Get the complete story log."""
        return self.story_log.copy()
    
    def get_recent_story(self, max_events: int = 20) -> List[Dict[str, Any]]:
        """Get recent story events."""
        return self.story_log[-max_events:] if self.story_log else []
    
    def get_context_for_ai(self) -> Dict[str, Any]:
        """
        Get formatted context for AI decision-making.
        
        Returns:
            Dictionary containing decision history and story context
        """
        return {
            'recent_decisions': self.get_decision_history(),
            'recent_story': self.get_recent_story(),
            'total_decisions': len(self.decision_history),
            'total_story_events': len(self.story_log),
            'last_decision_time': self.decision_history[-1]['timestamp'] if self.decision_history else None
        }
    
    def save_to_file(self) -> None:
        """Save history to files."""
        try:
            # Convert to JSON-serializable format
            serializable_decisions = self._make_serializable(self.decision_history)
            serializable_story = self._make_serializable(self.story_log)
            
            # Save decision history
            decision_file = self.logs_dir / "decision_history.json"
            with open(decision_file, 'w') as f:
                json.dump(serializable_decisions, f, indent=2)
            
            # Save story log
            story_file = self.logs_dir / "story_log.json"
            with open(story_file, 'w') as f:
                json.dump(serializable_story, f, indent=2)
            
            logger.info(f"History saved to {self.logs_dir}")
            
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def _make_serializable(self, obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        else:
            # Convert other types to string
            return str(obj)
    
    def load_from_file(self) -> None:
        """Load history from files."""
        try:
            # Load decision history
            decision_file = self.logs_dir / "decision_history.json"
            if decision_file.exists():
                with open(decision_file, 'r') as f:
                    self.decision_history = json.load(f)
                logger.info(f"Loaded {len(self.decision_history)} decisions from file")
            
            # Load story log
            story_file = self.logs_dir / "story_log.json"
            if story_file.exists():
                with open(story_file, 'r') as f:
                    self.story_log = json.load(f)
                logger.info(f"Loaded {len(self.story_log)} story events from file")
                
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    def get_summary(self) -> str:
        """Get a text summary of recent activity."""
        if not self.decision_history and not self.story_log:
            return "No history available yet."
        
        summary = []
        
        # Recent decisions summary
        if self.decision_history:
            recent_decisions = self.decision_history[-3:]  # Last 3 decisions
            summary.append("Recent Decisions:")
            for decision in recent_decisions:
                sequence_str = ", ".join([action['button'] for action in decision['sequence']])
                success_str = "✅" if decision['success'] else "❌"
                summary.append(f"  {success_str} Decision #{decision['decision_id']}: {sequence_str} ({decision['reasoning'][:50]}...)")
        
        # Recent story summary
        if self.story_log:
            recent_story = self.story_log[-5:]  # Last 5 story events
            summary.append("\nRecent Story Events:")
            for event in recent_story:
                summary.append(f"  📖 {event['type']}: {event['content'][:60]}...")
        
        return "\n".join(summary)
