"""
Temporal Brain - Time-based Reasoning

This brain module handles temporal reasoning, episode tracking,
and understanding of sequences and causality over time.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
import time
from enum import Enum

logger = logging.getLogger(__name__)


class TemporalRelation(Enum):
    """Types of temporal relationships."""
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    OVERLAPS = "overlaps"
    STARTS = "starts"
    FINISHES = "finishes"
    EQUALS = "equals"
    CAUSED_BY = "caused_by"
    CAUSES = "causes"


@dataclass
class Event:
    """Represents a temporal event."""
    id: str
    description: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None
        
    @property
    def is_ongoing(self) -> bool:
        return self.end_time is None


@dataclass
class Episode:
    """A sequence of related events forming a coherent episode."""
    id: str
    events: List[Event]
    start_time: float
    end_time: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    causal_links: List[Tuple[str, str]] = field(default_factory=list)  # (cause_event_id, effect_event_id)
    
    def add_event(self, event: Event):
        self.events.append(event)
        self.events.sort(key=lambda e: e.start_time)
        
    def add_causal_link(self, cause_id: str, effect_id: str):
        self.causal_links.append((cause_id, effect_id))


@dataclass
class TemporalPattern:
    """A learned temporal pattern."""
    name: str
    event_sequence: List[str]  # Event types in order
    typical_durations: List[float]  # Typical duration for each event
    confidence: float
    occurrences: int = 0


class TemporalBrain:
    """
    The Temporal brain handles time-based reasoning and episode understanding.
    
    Core responsibilities:
    - Track events and their temporal relationships
    - Identify episodes and causal chains
    - Learn temporal patterns
    - Predict future events based on past patterns
    - Reason about causality
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.events: Dict[str, Event] = {}
        self.episodes: Dict[str, Episode] = {}
        self.active_episodes: Set[str] = set()
        self.event_history: deque = deque(maxlen=max_history)
        self.temporal_relations: Dict[Tuple[str, str], TemporalRelation] = {}
        self.learned_patterns: Dict[str, TemporalPattern] = {}
        self.causal_graph: defaultdict = defaultdict(list)  # event_id -> [caused_event_ids]
        
    def record_event(self, event_id: str, description: str, 
                    attributes: Dict[str, Any] = None) -> Event:
        """
        Record a new event starting now.
        
        Args:
            event_id: Unique identifier for the event
            description: What happened
            attributes: Additional event properties
            
        Returns:
            The created Event
        """
        event = Event(
            id=event_id,
            description=description,
            start_time=time.time(),
            attributes=attributes or {}
        )
        
        self.events[event_id] = event
        self.event_history.append(event_id)
        
        # Check if this event fits any episodes
        self._update_episodes(event)
        
        logger.debug(f"Recorded event: {event_id} - {description}")
        return event
        
    def end_event(self, event_id: str) -> bool:
        """
        Mark an event as ended.
        
        Args:
            event_id: Event to end
            
        Returns:
            True if successful
        """
        if event_id in self.events and self.events[event_id].is_ongoing:
            self.events[event_id].end_time = time.time()
            
            # Check for pattern completion
            self._check_pattern_completion(event_id)
            
            return True
        return False
        
    def create_episode(self, episode_id: str, initial_event_id: str,
                      context: Dict[str, Any] = None) -> Episode:
        """
        Create a new episode starting with an event.
        
        Args:
            episode_id: Unique identifier for the episode
            initial_event_id: First event in the episode
            context: Episode context
            
        Returns:
            The created Episode
        """
        if initial_event_id not in self.events:
            raise ValueError(f"Unknown event: {initial_event_id}")
            
        event = self.events[initial_event_id]
        episode = Episode(
            id=episode_id,
            events=[event],
            start_time=event.start_time,
            context=context or {}
        )
        
        self.episodes[episode_id] = episode
        self.active_episodes.add(episode_id)
        
        logger.debug(f"Created episode: {episode_id}")
        return episode
        
    def add_to_episode(self, episode_id: str, event_id: str) -> bool:
        """
        Add an event to an existing episode.
        
        Returns:
            True if successful
        """
        if episode_id in self.episodes and event_id in self.events:
            episode = self.episodes[episode_id]
            event = self.events[event_id]
            
            episode.add_event(event)
            return True
        return False
        
    def end_episode(self, episode_id: str) -> bool:
        """
        Mark an episode as ended.
        
        Returns:
            True if successful
        """
        if episode_id in self.episodes and episode_id in self.active_episodes:
            self.episodes[episode_id].end_time = time.time()
            self.active_episodes.remove(episode_id)
            
            # Learn from this episode
            self._learn_from_episode(self.episodes[episode_id])
            
            return True
        return False
        
    def establish_causality(self, cause_event_id: str, effect_event_id: str,
                          confidence: float = 0.8):
        """
        Establish a causal relationship between events.
        
        Args:
            cause_event_id: The causing event
            effect_event_id: The effect event
            confidence: Confidence in the causal link
        """
        if cause_event_id not in self.events or effect_event_id not in self.events:
            return
            
        # Verify temporal ordering
        cause = self.events[cause_event_id]
        effect = self.events[effect_event_id]
        
        if cause.start_time >= effect.start_time:
            logger.warning(f"Cannot establish causality: cause after effect")
            return
            
        # Record causal link
        self.causal_graph[cause_event_id].append(effect_event_id)
        self.temporal_relations[(cause_event_id, effect_event_id)] = TemporalRelation.CAUSES
        
        # Update episodes
        for episode in self.episodes.values():
            if cause_event_id in [e.id for e in episode.events] and \
               effect_event_id in [e.id for e in episode.events]:
                episode.add_causal_link(cause_event_id, effect_event_id)
                
    def query_temporal_relation(self, event1_id: str, event2_id: str) -> Optional[TemporalRelation]:
        """
        Query the temporal relationship between two events.
        
        Returns:
            The temporal relation or None
        """
        # Check cached relations
        if (event1_id, event2_id) in self.temporal_relations:
            return self.temporal_relations[(event1_id, event2_id)]
            
        # Compute relation
        if event1_id in self.events and event2_id in self.events:
            relation = self._compute_temporal_relation(
                self.events[event1_id],
                self.events[event2_id]
            )
            
            # Cache it
            self.temporal_relations[(event1_id, event2_id)] = relation
            return relation
            
        return None
        
    def predict_next_events(self, current_context: List[str], 
                          top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Predict likely next events based on learned patterns.
        
        Args:
            current_context: Recent event types
            top_k: Number of predictions to return
            
        Returns:
            List of (event_type, probability) tuples
        """
        predictions = defaultdict(float)
        
        # Check each learned pattern
        for pattern in self.learned_patterns.values():
            # See if current context matches pattern prefix
            for i in range(len(pattern.event_sequence) - 1):
                prefix = pattern.event_sequence[:i+1]
                if self._matches_suffix(current_context, prefix):
                    # Predict next event in pattern
                    next_event = pattern.event_sequence[i+1]
                    predictions[next_event] += pattern.confidence * pattern.occurrences
                    
        # Normalize and sort
        total = sum(predictions.values())
        if total > 0:
            predictions = {k: v/total for k, v in predictions.items()}
            
        sorted_predictions = sorted(
            predictions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_predictions[:top_k]
        
    def find_similar_episodes(self, episode_id: str, 
                            similarity_threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Find episodes similar to a given episode.
        
        Args:
            episode_id: Reference episode
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of (episode_id, similarity_score) tuples
        """
        if episode_id not in self.episodes:
            return []
            
        reference = self.episodes[episode_id]
        similar = []
        
        for other_id, other_episode in self.episodes.items():
            if other_id == episode_id:
                continue
                
            similarity = self._compute_episode_similarity(reference, other_episode)
            if similarity >= similarity_threshold:
                similar.append((other_id, similarity))
                
        return sorted(similar, key=lambda x: x[1], reverse=True)
        
    def get_causal_chain(self, event_id: str) -> List[List[str]]:
        """
        Get all causal chains starting from an event.
        
        Returns:
            List of causal chains (each chain is a list of event IDs)
        """
        chains = []
        
        def trace_chain(current_id: str, current_chain: List[str]):
            current_chain = current_chain + [current_id]
            
            if current_id in self.causal_graph:
                effects = self.causal_graph[current_id]
                if not effects:
                    chains.append(current_chain)
                else:
                    for effect_id in effects:
                        trace_chain(effect_id, current_chain)
            else:
                chains.append(current_chain)
                
        trace_chain(event_id, [])
        return chains
        
    def explain_timing(self, event_id: str) -> Dict[str, Any]:
        """
        Explain why an event happened when it did.
        
        Returns:
            Explanation with causal factors and temporal context
        """
        if event_id not in self.events:
            return {"error": "Unknown event"}
            
        event = self.events[event_id]
        explanation = {
            "event": event.description,
            "timing": {
                "start": event.start_time,
                "duration": event.duration
            },
            "causal_factors": [],
            "temporal_context": [],
            "patterns": []
        }
        
        # Find causal factors
        for cause_id, effects in self.causal_graph.items():
            if event_id in effects:
                cause = self.events[cause_id]
                explanation["causal_factors"].append({
                    "cause": cause.description,
                    "delay": event.start_time - cause.start_time
                })
                
        # Find temporal context (what else was happening)
        for other_id, other_event in self.events.items():
            if other_id == event_id:
                continue
                
            relation = self.query_temporal_relation(other_id, event_id)
            if relation in [TemporalRelation.DURING, TemporalRelation.OVERLAPS]:
                explanation["temporal_context"].append({
                    "event": other_event.description,
                    "relation": relation.value
                })
                
        # Find matching patterns
        event_type = event.attributes.get('type', event.description)
        for pattern in self.learned_patterns.values():
            if event_type in pattern.event_sequence:
                explanation["patterns"].append(pattern.name)
                
        return explanation
        
    def _update_episodes(self, event: Event):
        """Update active episodes with new event."""
        event_type = event.attributes.get('type', event.description)
        
        # Check each active episode
        for episode_id in list(self.active_episodes):
            episode = self.episodes[episode_id]
            
            # Simple heuristic: add if temporally close and similar context
            if episode.events:
                last_event = episode.events[-1]
                time_gap = event.start_time - last_event.start_time
                
                # If within 5 seconds and similar context
                if time_gap < 5.0:
                    self.add_to_episode(episode_id, event.id)
                    
    def _check_pattern_completion(self, event_id: str):
        """Check if completing this event completes a pattern."""
        # Look at recent events
        recent_events = list(self.event_history)[-10:]
        
        if len(recent_events) < 2:
            return
            
        # Extract event types
        event_types = []
        for eid in recent_events:
            if eid in self.events:
                event_types.append(
                    self.events[eid].attributes.get('type', self.events[eid].description)
                )
                
        # Check against known patterns
        for pattern in self.learned_patterns.values():
            if self._matches_suffix(event_types, pattern.event_sequence):
                pattern.occurrences += 1
                logger.debug(f"Pattern '{pattern.name}' completed (count: {pattern.occurrences})")
                
    def _learn_from_episode(self, episode: Episode):
        """Learn patterns from a completed episode."""
        if len(episode.events) < 2:
            return
            
        # Extract event sequence
        event_types = []
        durations = []
        
        for event in episode.events:
            event_types.append(event.attributes.get('type', event.description))
            if event.duration:
                durations.append(event.duration)
                
        # Create pattern name
        pattern_name = f"pattern_{len(self.learned_patterns)}"
        
        # Check if pattern already exists
        for existing in self.learned_patterns.values():
            if existing.event_sequence == event_types:
                existing.occurrences += 1
                existing.confidence = min(0.95, existing.confidence + 0.05)
                return
                
        # New pattern
        pattern = TemporalPattern(
            name=pattern_name,
            event_sequence=event_types,
            typical_durations=durations,
            confidence=0.5,
            occurrences=1
        )
        
        self.learned_patterns[pattern_name] = pattern
        logger.info(f"Learned new temporal pattern: {pattern_name}")
        
    def _compute_temporal_relation(self, event1: Event, event2: Event) -> TemporalRelation:
        """Compute Allen's temporal relation between two events."""
        # Simplified implementation
        if event1.end_time and event2.end_time:
            if event1.end_time < event2.start_time:
                return TemporalRelation.BEFORE
            elif event2.end_time < event1.start_time:
                return TemporalRelation.AFTER
            elif event1.start_time == event2.start_time and event1.end_time == event2.end_time:
                return TemporalRelation.EQUALS
            elif event1.start_time < event2.start_time and event1.end_time > event2.end_time:
                return TemporalRelation.DURING
            else:
                return TemporalRelation.OVERLAPS
        else:
            # Handle ongoing events
            if event1.start_time < event2.start_time:
                return TemporalRelation.BEFORE
            else:
                return TemporalRelation.AFTER
                
    def _compute_episode_similarity(self, ep1: Episode, ep2: Episode) -> float:
        """Compute similarity between two episodes."""
        # Simple similarity based on event types
        types1 = [e.attributes.get('type', e.description) for e in ep1.events]
        types2 = [e.attributes.get('type', e.description) for e in ep2.events]
        
        # Jaccard similarity
        set1, set2 = set(types1), set(types2)
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
        
    def _matches_suffix(self, sequence: List[str], pattern: List[str]) -> bool:
        """Check if pattern matches the suffix of sequence."""
        if len(pattern) > len(sequence):
            return False
        return sequence[-len(pattern):] == pattern