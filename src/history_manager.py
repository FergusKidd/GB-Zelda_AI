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
        self.npc_interactions: Dict[str, Dict[str, Any]] = {}  # Track NPC interactions by location
        self.position_history: List[Dict[str, Any]] = []  # Track recent positions for stuck detection
        self.current_plan: Optional[Dict[str, Any]] = None  # Current high-level plan
        self.plan_cycle_count: int = 0  # Count decisions since last plan update
        self.visited_rooms: set = set()  # Track all rooms that have been visited
        
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
        
        # Track NPC interactions based on location
        if event_type == 'dialogue' and context:
            self._track_npc_interaction(content, context)
    
    def _track_npc_interaction(self, dialogue: str, context: Dict[str, Any]) -> None:
        """
        Track NPC interactions by location to prevent repeated conversations.
        
        Args:
            dialogue: The dialogue content
            context: Context containing position and room info
        """
        # Extract location info from context
        position_x = context.get('position_x', 0)
        position_y = context.get('position_y', 0)
        room_id = context.get('room_id', 0)
        
        # Create a location key (room + approximate position)
        # Use a grid system to group nearby positions (16-pixel grids)
        grid_x = position_x // 16 if position_x else 0
        grid_y = position_y // 16 if position_y else 0
        location_key = f"room_{room_id}_x{grid_x}_y{grid_y}"
        
        # Track this interaction
        if location_key not in self.npc_interactions:
            self.npc_interactions[location_key] = {
                'first_interaction': time.time(),
                'dialogue_snippets': [],
                'interaction_count': 0,
                'position': {'x': position_x, 'y': position_y, 'room': room_id},
                'character_description': ''
            }
        
        interaction = self.npc_interactions[location_key]
        interaction['last_interaction'] = time.time()
        interaction['interaction_count'] += 1
        
        # Store unique dialogue snippets (first 50 chars)
        snippet = dialogue[:50] if dialogue else ""
        if snippet and snippet not in interaction['dialogue_snippets']:
            interaction['dialogue_snippets'].append(snippet)
        
        # Limit to 5 snippets per location
        if len(interaction['dialogue_snippets']) > 5:
            interaction['dialogue_snippets'] = interaction['dialogue_snippets'][-5:]
        
        # Try to extract character description from current plan
        if self.current_plan and 'goal' in self.current_plan:
            goal = self.current_plan['goal']
            # Store first few words that might be a character description
            if not interaction['character_description'] and len(goal) > 20:
                # Extract description (rough heuristic: text between "talk to" and "in/at/near")
                import re
                match = re.search(r'talk to (the )?([^\.]+?)(?:\s+in|\s+at|\s+near|$)', goal, re.IGNORECASE)
                if match:
                    interaction['character_description'] = match.group(2).strip()
        
        logger.debug(f"📍 NPC interaction tracked at {location_key} (count: {interaction['interaction_count']})")
        
        # Add repeat interaction warning to story log
        if interaction['interaction_count'] >= 2:
            char_desc = interaction.get('character_description', 'NPC')
            repeat_note = f"[Already spoken to {char_desc} {interaction['interaction_count']}x at X={position_x}, Y={position_y}]"
            self.story_log.append({
                'timestamp': time.time(),
                'event_id': len(self.story_log) + 1,
                'type': 'npc_repeat',
                'content': repeat_note,
                'context': {
                    'location': location_key,
                    'count': interaction['interaction_count'],
                    'character': char_desc
                }
            })
            logger.info(f"📖 Story note: {repeat_note}")
    
    def check_room_visit(self, room_id: int) -> Dict[str, Any]:
        """
        Check if this room has been visited before and update tracking.
        
        Args:
            room_id: The room ID to check
            
        Returns:
            Dictionary with 'is_new' boolean and 'visit_count'
        """
        is_new = room_id not in self.visited_rooms
        
        # Add to visited rooms
        self.visited_rooms.add(room_id)
        
        # Count how many times we've been here (approximate from position history)
        visit_count = sum(1 for pos in self.position_history if pos.get('room') == room_id)
        
        result = {
            'is_new': is_new,
            'visit_count': visit_count + 1,  # +1 for current visit
            'total_rooms_visited': len(self.visited_rooms)
        }
        
        if is_new:
            logger.info(f"🆕 New room discovered: Room {room_id} (total: {len(self.visited_rooms)} rooms)")
        else:
            logger.debug(f"🔄 Revisiting Room {room_id} (visit #{visit_count + 1})")
        
        return result
    
    def check_if_stuck(self, game_state: Dict[str, Any]) -> bool:
        """
        Check if the player is stuck in the same position.
        
        Args:
            game_state: Current game state with position info
            
        Returns:
            True if stuck (same position 5+ times without dialogue)
        """
        position_x = game_state.get('position_x', 0)
        position_y = game_state.get('position_y', 0)
        room_id = game_state.get('room_id', 0)
        in_text_box = game_state.get('in_text_box', False)
        
        # Add current position to history
        self.position_history.append({
            'x': position_x,
            'y': position_y,
            'room': room_id,
            'in_text_box': in_text_box,
            'timestamp': time.time()
        })
        
        # Keep only last 8 positions
        if len(self.position_history) > 8:
            self.position_history = self.position_history[-8:]
        
        # Need at least 5 positions to check (increased from 3)
        if len(self.position_history) < 5:
            return False
        
        # Check last 5 positions (excluding dialogue)
        recent_positions = [p for p in self.position_history[-5:] if not p['in_text_box']]
        
        # Need at least 5 non-dialogue positions
        if len(recent_positions) < 5:
            return False
        
        # Check if all 5 positions are the same (within 4 pixels tolerance - tighter than before)
        first_pos = recent_positions[0]
        is_stuck = all(
            abs(p['x'] - first_pos['x']) <= 4 and 
            abs(p['y'] - first_pos['y']) <= 4 and
            p['room'] == first_pos['room']
            for p in recent_positions
        )
        
        if is_stuck:
            logger.warning(f"⚠️  STUCK DETECTED at Room {room_id}, X={position_x}, Y={position_y}")
        
        return is_stuck
    
    def update_plan(self, plan: Dict[str, Any]) -> None:
        """
        Update the current high-level plan.
        
        Args:
            plan: New plan from the planning AI
        """
        self.current_plan = {
            'goal': plan.get('goal', ''),
            'steps': plan.get('steps', []),
            'reasoning': plan.get('reasoning', ''),
            'created_at': time.time(),
            'cycle_count': self.plan_cycle_count
        }
        self.plan_cycle_count = 0  # Reset cycle count
        logger.info(f"📋 New plan created: {self.current_plan['goal']}")
    
    def increment_plan_cycle(self) -> int:
        """
        Increment the plan cycle counter.
        
        Returns:
            Current cycle count
        """
        self.plan_cycle_count += 1
        return self.plan_cycle_count
    
    def should_update_plan(self, max_cycles: int = 5) -> bool:
        """
        Check if it's time to update the plan.
        
        Args:
            max_cycles: Maximum cycles before plan refresh
            
        Returns:
            True if plan should be updated
        """
        return self.current_plan is None or self.plan_cycle_count >= max_cycles
    
    def get_current_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current plan."""
        return self.current_plan
    
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
            Dictionary containing decision history, story context, NPC interactions, current plan, and room visit info
        """
        return {
            'recent_decisions': self.get_decision_history(),
            'recent_story': self.get_recent_story(),
            'npc_interactions': self.get_npc_interaction_summary(),
            'current_plan': self.current_plan,
            'visited_rooms': self.visited_rooms,
            'total_rooms_visited': len(self.visited_rooms),
            'total_decisions': len(self.decision_history),
            'total_story_events': len(self.story_log),
            'last_decision_time': self.decision_history[-1]['timestamp'] if self.decision_history else None
        }
    
    def get_npc_interaction_summary(self) -> Dict[str, Any]:
        """
        Get summary of NPC interactions for AI context.
        
        Returns:
            Dictionary with interaction counts and locations
        """
        # Find locations with repeated interactions
        repeated_npcs = []
        for location_key, interaction in self.npc_interactions.items():
            if interaction['interaction_count'] >= 2:  # Talked to same NPC 2+ times
                repeated_npcs.append({
                    'location': location_key,
                    'count': interaction['interaction_count'],
                    'position': interaction['position'],
                    'dialogue_snippet': interaction['dialogue_snippets'][0] if interaction['dialogue_snippets'] else "Unknown"
                })
        
        return {
            'repeated_interactions': repeated_npcs,
            'total_npcs_talked_to': len(self.npc_interactions)
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
