"""
Markovian Update - Temporal state transition modeling.

This module handles Markovian updates for temporal reasoning,
modeling state transitions and probabilistic temporal evolution.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class State:
    """Represents a state in the Markov model."""
    id: str
    features: Dict[str, Any]
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
        
    def __eq__(self, other):
        return isinstance(other, State) and self.id == other.id


@dataclass
class Transition:
    """Represents a transition between states."""
    from_state: str
    to_state: str
    probability: float
    duration: float  # Expected duration
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarkovianUpdater:
    """
    Handles Markovian updates for temporal state evolution.
    
    This class models temporal dynamics using Markov chains,
    learning transition probabilities from observed sequences.
    """
    
    def __init__(self, memory_length: int = 1):
        """
        Initialize the Markovian updater.
        
        Args:
            memory_length: Order of the Markov chain (1 = first-order)
        """
        self.memory_length = memory_length
        self.states: Dict[str, State] = {}
        self.transitions: Dict[Tuple[str, ...], List[Transition]] = defaultdict(list)
        self.transition_counts: Dict[Tuple[str, ...], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.state_durations: Dict[str, List[float]] = defaultdict(list)
        self.current_state: Optional[State] = None
        self.state_history: List[str] = []
        
    def add_state(self, state: State):
        """Add a new state to the model."""
        self.states[state.id] = state
        logger.debug(f"Added state: {state.id}")
        
    def observe_transition(self, from_state: State, to_state: State, duration: float):
        """
        Observe a state transition.
        
        Args:
            from_state: Starting state
            to_state: Ending state
            duration: Time taken for transition
        """
        # Ensure states are registered
        if from_state.id not in self.states:
            self.add_state(from_state)
        if to_state.id not in self.states:
            self.add_state(to_state)
            
        # Update history
        if self.current_state != from_state:
            self.state_history.append(from_state.id)
            
        self.state_history.append(to_state.id)
        self.current_state = to_state
        
        # Get context (previous states for higher-order Markov)
        context = self._get_context(from_state.id)
        
        # Update counts
        self.transition_counts[context][to_state.id] += 1
        
        # Record duration
        self.state_durations[from_state.id].append(duration)
        
        # Update transition probabilities
        self._update_transitions(context)
        
        logger.debug(f"Observed transition: {from_state.id} -> {to_state.id} (duration: {duration})")
        
    def predict_next_state(self, current_state: Optional[State] = None,
                          top_k: int = 3) -> List[Tuple[State, float]]:
        """
        Predict likely next states.
        
        Args:
            current_state: Current state (uses self.current_state if None)
            top_k: Number of predictions to return
            
        Returns:
            List of (state, probability) tuples
        """
        if current_state is None:
            current_state = self.current_state
            
        if current_state is None:
            return []
            
        # Get context
        context = self._get_context(current_state.id)
        
        # Get possible transitions
        if context not in self.transitions:
            # No data for this context, use uniform prior
            all_states = list(self.states.values())
            prob = 1.0 / len(all_states) if all_states else 0.0
            return [(s, prob) for s in all_states[:top_k]]
            
        # Get transitions sorted by probability
        transitions = self.transitions[context]
        transitions.sort(key=lambda t: t.probability, reverse=True)
        
        predictions = []
        for trans in transitions[:top_k]:
            if trans.to_state in self.states:
                predictions.append((self.states[trans.to_state], trans.probability))
                
        return predictions
        
    def predict_duration(self, state_id: str) -> Dict[str, float]:
        """
        Predict duration for a state.
        
        Args:
            state_id: State to predict duration for
            
        Returns:
            Dict with mean, std, and percentiles
        """
        if state_id not in self.state_durations or not self.state_durations[state_id]:
            return {
                'mean': 0.0,
                'std': 0.0,
                'median': 0.0,
                'p25': 0.0,
                'p75': 0.0
            }
            
        durations = np.array(self.state_durations[state_id])
        
        return {
            'mean': np.mean(durations),
            'std': np.std(durations),
            'median': np.median(durations),
            'p25': np.percentile(durations, 25),
            'p75': np.percentile(durations, 75)
        }
        
    def find_state_sequence(self, start_state: str, end_state: str,
                          max_length: int = 10) -> List[List[str]]:
        """
        Find probable paths between states.
        
        Args:
            start_state: Starting state ID
            end_state: Target state ID
            max_length: Maximum path length
            
        Returns:
            List of possible paths
        """
        if start_state not in self.states or end_state not in self.states:
            return []
            
        paths = []
        
        def search(current: str, path: List[str], visited: set):
            if len(path) > max_length:
                return
                
            if current == end_state:
                paths.append(path)
                return
                
            visited.add(current)
            
            # Get possible next states
            context = self._get_context_from_path(path)
            if context in self.transitions:
                for trans in self.transitions[context]:
                    if trans.to_state not in visited and trans.probability > 0.1:
                        search(trans.to_state, path + [trans.to_state], visited.copy())
                        
        search(start_state, [start_state], set())
        
        # Sort by total probability
        scored_paths = []
        for path in paths:
            score = self._score_path(path)
            scored_paths.append((path, score))
            
        scored_paths.sort(key=lambda x: x[1], reverse=True)
        
        return [path for path, _ in scored_paths[:5]]  # Top 5 paths
        
    def get_steady_state(self) -> Dict[str, float]:
        """
        Calculate steady-state distribution.
        
        Returns:
            Dict mapping state IDs to steady-state probabilities
        """
        if not self.states:
            return {}
            
        # For simplicity, use empirical frequencies
        # Full implementation would solve π = πP
        
        total_visits = defaultdict(int)
        for state_id in self.state_history:
            total_visits[state_id] += 1
            
        total = sum(total_visits.values())
        if total == 0:
            return {state_id: 1.0/len(self.states) for state_id in self.states}
            
        return {
            state_id: count/total 
            for state_id, count in total_visits.items()
        }
        
    def detect_cycles(self, min_length: int = 2, min_occurrences: int = 2) -> List[List[str]]:
        """
        Detect recurring cycles in state transitions.
        
        Args:
            min_length: Minimum cycle length
            min_occurrences: Minimum times cycle must appear
            
        Returns:
            List of detected cycles
        """
        cycles = defaultdict(int)
        
        # Scan history for repeating patterns
        for start in range(len(self.state_history)):
            for length in range(min_length, min(len(self.state_history) - start, 20)):
                pattern = tuple(self.state_history[start:start + length])
                
                # Check if this pattern appears again
                for check_start in range(start + length, len(self.state_history) - length + 1):
                    if tuple(self.state_history[check_start:check_start + length]) == pattern:
                        cycles[pattern] += 1
                        
        # Filter by minimum occurrences
        detected = []
        for pattern, count in cycles.items():
            if count >= min_occurrences:
                detected.append(list(pattern))
                
        return detected
        
    def merge_similar_states(self, similarity_threshold: float = 0.9):
        """
        Merge states that are very similar.
        
        Args:
            similarity_threshold: Minimum similarity to merge
        """
        # Group similar states
        groups = []
        assigned = set()
        
        for state1_id in self.states:
            if state1_id in assigned:
                continue
                
            group = [state1_id]
            assigned.add(state1_id)
            
            for state2_id in self.states:
                if state2_id in assigned:
                    continue
                    
                if self._compute_similarity(state1_id, state2_id) >= similarity_threshold:
                    group.append(state2_id)
                    assigned.add(state2_id)
                    
            if len(group) > 1:
                groups.append(group)
                
        # Merge groups
        for group in groups:
            self._merge_states(group)
            
    def _get_context(self, current_state: str) -> Tuple[str, ...]:
        """Get context for Markov chain (handles memory length)."""
        if self.memory_length == 1:
            return (current_state,)
            
        # Get previous states from history
        context = [current_state]
        history_idx = len(self.state_history) - 1
        
        # Find current state in history and backtrack
        while history_idx >= 0 and self.state_history[history_idx] != current_state:
            history_idx -= 1
            
        # Collect previous states
        for i in range(1, self.memory_length):
            if history_idx - i >= 0:
                context.insert(0, self.state_history[history_idx - i])
            else:
                context.insert(0, "<START>")
                
        return tuple(context)
        
    def _get_context_from_path(self, path: List[str]) -> Tuple[str, ...]:
        """Get context from a path."""
        if len(path) >= self.memory_length:
            return tuple(path[-self.memory_length:])
        else:
            padding = ["<START>"] * (self.memory_length - len(path))
            return tuple(padding + path)
            
    def _update_transitions(self, context: Tuple[str, ...]):
        """Update transition probabilities for a context."""
        counts = self.transition_counts[context]
        total = sum(counts.values())
        
        if total == 0:
            return
            
        # Clear old transitions
        self.transitions[context] = []
        
        # Create new transitions with updated probabilities
        for to_state, count in counts.items():
            prob = count / total
            
            # Estimate duration
            from_state = context[-1]
            durations = self.state_durations.get(from_state, [1.0])
            avg_duration = np.mean(durations) if durations else 1.0
            
            transition = Transition(
                from_state=from_state,
                to_state=to_state,
                probability=prob,
                duration=avg_duration
            )
            
            self.transitions[context].append(transition)
            
    def _score_path(self, path: List[str]) -> float:
        """Score a path based on transition probabilities."""
        if len(path) < 2:
            return 1.0
            
        score = 1.0
        
        for i in range(len(path) - 1):
            context = self._get_context_from_path(path[:i+1])
            next_state = path[i + 1]
            
            # Find transition probability
            trans_prob = 0.01  # Small default
            
            if context in self.transitions:
                for trans in self.transitions[context]:
                    if trans.to_state == next_state:
                        trans_prob = trans.probability
                        break
                        
            score *= trans_prob
            
        return score
        
    def _compute_similarity(self, state1_id: str, state2_id: str) -> float:
        """Compute similarity between two states."""
        if state1_id not in self.states or state2_id not in self.states:
            return 0.0
            
        state1 = self.states[state1_id]
        state2 = self.states[state2_id]
        
        # Simple feature comparison
        common_features = set(state1.features.keys()) & set(state2.features.keys())
        if not common_features:
            return 0.0
            
        matches = sum(1 for f in common_features 
                     if state1.features[f] == state2.features[f])
                     
        return matches / len(common_features)
        
    def _merge_states(self, state_ids: List[str]):
        """Merge multiple states into one."""
        if len(state_ids) < 2:
            return
            
        # Keep first state as representative
        keep_id = state_ids[0]
        merge_ids = state_ids[1:]
        
        logger.info(f"Merging states {merge_ids} into {keep_id}")
        
        # Update all references
        for merge_id in merge_ids:
            # Update history
            self.state_history = [keep_id if s == merge_id else s 
                                 for s in self.state_history]
                                 
            # Update transitions
            new_transitions = defaultdict(list)
            new_counts = defaultdict(lambda: defaultdict(int))
            
            for context, transitions in self.transitions.items():
                new_context = tuple(keep_id if s == merge_id else s for s in context)
                
                for trans in transitions:
                    new_to = keep_id if trans.to_state == merge_id else trans.to_state
                    new_transitions[new_context].append(
                        Transition(trans.from_state, new_to, trans.probability, trans.duration)
                    )
                    
            self.transitions = dict(new_transitions)
            
            # Update counts
            for context, counts in self.transition_counts.items():
                new_context = tuple(keep_id if s == merge_id else s for s in context)
                for to_state, count in counts.items():
                    new_to = keep_id if to_state == merge_id else to_state
                    new_counts[new_context][new_to] += count
                    
            self.transition_counts = new_counts
            
            # Merge durations
            if merge_id in self.state_durations:
                self.state_durations[keep_id].extend(self.state_durations[merge_id])
                del self.state_durations[merge_id]
                
            # Remove merged state
            if merge_id in self.states:
                del self.states[merge_id]