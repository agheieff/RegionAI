"""
Bayesian Brain - "What is true?"

This brain module handles probabilistic reasoning and belief updates.
It maintains and updates beliefs about the world using Bayesian inference.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from ..config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    """Represents a probabilistic belief with beta distribution parameters."""
    alpha: float  # Evidence for
    beta: float   # Evidence against
    
    @property
    def mean(self) -> float:
        """Expected value of the beta distribution."""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def confidence(self) -> float:
        """Measure of confidence based on total evidence."""
        total = self.alpha + self.beta
        return min(1.0, total / 100.0)  # Normalize to [0,1]


class BayesianBrain:
    """
    The Bayesian brain handles probabilistic reasoning about what is true.
    
    Core responsibilities:
    - Maintain beliefs about concepts and relationships
    - Update beliefs based on new evidence
    - Reason about uncertainty
    - Answer queries about what is likely true
    """
    
    def __init__(self, config: RegionAIConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.beliefs: Dict[str, Belief] = {}
        self.relationships: Dict[Tuple[str, str, str], Belief] = {}
        self._evidence_history: List[Dict] = []
        
    def observe(self, concept: str, evidence_positive: bool, credibility: float = 1.0):
        """
        Update belief about a concept based on observation.
        
        Args:
            concept: The concept being observed
            evidence_positive: Whether evidence supports the concept
            credibility: How credible the evidence source is [0,1]
        """
        if concept not in self.beliefs:
            self.beliefs[concept] = Belief(
                alpha=self.config.prior_alpha,
                beta=self.config.prior_beta
            )
        
        # Compute evidence strength
        if evidence_positive:
            evidence_strength = self.config.positive_evidence_strength * credibility
            self.beliefs[concept].alpha += evidence_strength
        else:
            evidence_strength = self.config.negative_evidence_strength * credibility
            self.beliefs[concept].beta += evidence_strength
            
        # Record evidence
        self._evidence_history.append({
            'concept': concept,
            'positive': evidence_positive,
            'credibility': credibility,
            'strength': evidence_strength
        })
        
        logger.debug(f"Updated belief in '{concept}': {self.beliefs[concept].mean:.3f}")
        
    def observe_relationship(self, source: str, relation: str, target: str,
                           evidence_positive: bool, credibility: float = 1.0):
        """
        Update belief about a relationship between concepts.
        
        Args:
            source: Source concept
            relation: Type of relationship
            target: Target concept
            evidence_positive: Whether evidence supports the relationship
            credibility: Evidence credibility [0,1]
        """
        key = (source, relation, target)
        if key not in self.relationships:
            self.relationships[key] = Belief(
                alpha=self.config.prior_alpha,
                beta=self.config.prior_beta
            )
        
        # Update belief
        if evidence_positive:
            evidence_strength = self.config.relational_evidence_strength * credibility
            self.relationships[key].alpha += evidence_strength
        else:
            evidence_strength = self.config.relational_evidence_strength * credibility
            self.relationships[key].beta += evidence_strength
            
        logger.debug(
            f"Updated belief in '{source} {relation} {target}': "
            f"{self.relationships[key].mean:.3f}"
        )
        
    def query_belief(self, concept: str) -> Optional[float]:
        """
        Query the current belief probability for a concept.
        
        Returns:
            Probability [0,1] or None if unknown
        """
        if concept in self.beliefs:
            return self.beliefs[concept].mean
        return None
        
    def query_relationship(self, source: str, relation: str, target: str) -> Optional[float]:
        """
        Query belief in a specific relationship.
        
        Returns:
            Probability [0,1] or None if unknown
        """
        key = (source, relation, target)
        if key in self.relationships:
            return self.relationships[key].mean
        return None
        
    def get_confident_beliefs(self, min_confidence: float = 0.8) -> Dict[str, float]:
        """
        Get all beliefs we're confident about.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dict mapping concepts to their belief probabilities
        """
        confident = {}
        for concept, belief in self.beliefs.items():
            if belief.confidence >= min_confidence:
                confident[concept] = belief.mean
        return confident
        
    def explain_belief(self, concept: str) -> Dict[str, any]:
        """
        Explain the reasoning behind a belief.
        
        Returns:
            Dict with belief details and evidence summary
        """
        if concept not in self.beliefs:
            return {'error': 'Unknown concept'}
            
        belief = self.beliefs[concept]
        
        # Count evidence for this concept
        evidence_for = sum(1 for e in self._evidence_history 
                          if e['concept'] == concept and e['positive'])
        evidence_against = sum(1 for e in self._evidence_history 
                             if e['concept'] == concept and not e['positive'])
        
        return {
            'concept': concept,
            'probability': belief.mean,
            'confidence': belief.confidence,
            'evidence_for': evidence_for,
            'evidence_against': evidence_against,
            'alpha': belief.alpha,
            'beta': belief.beta,
            'interpretation': self._interpret_belief(belief.mean)
        }
        
    def _interpret_belief(self, probability: float) -> str:
        """Provide human-readable interpretation of belief strength."""
        if probability < 0.1:
            return "Almost certainly false"
        elif probability < 0.3:
            return "Probably false"
        elif probability < 0.5:
            return "Unlikely"
        elif probability < 0.7:
            return "Likely"
        elif probability < 0.9:
            return "Probably true"
        else:
            return "Almost certainly true"
            
    def merge_evidence(self, other_brain: 'BayesianBrain'):
        """
        Merge evidence from another Bayesian brain.
        
        Useful for combining knowledge from multiple sources.
        """
        # Merge concept beliefs
        for concept, other_belief in other_brain.beliefs.items():
            if concept not in self.beliefs:
                self.beliefs[concept] = Belief(
                    alpha=other_belief.alpha,
                    beta=other_belief.beta
                )
            else:
                # Combine evidence
                self.beliefs[concept].alpha += other_belief.alpha - self.config.prior_alpha
                self.beliefs[concept].beta += other_belief.beta - self.config.prior_beta
                
        # Merge relationship beliefs
        for key, other_belief in other_brain.relationships.items():
            if key not in self.relationships:
                self.relationships[key] = Belief(
                    alpha=other_belief.alpha,
                    beta=other_belief.beta
                )
            else:
                self.relationships[key].alpha += other_belief.alpha - self.config.prior_alpha
                self.relationships[key].beta += other_belief.beta - self.config.prior_beta
                
    def get_summary(self) -> Dict[str, any]:
        """Get a summary of the current belief state."""
        return {
            'total_concepts': len(self.beliefs),
            'total_relationships': len(self.relationships),
            'confident_beliefs': len(self.get_confident_beliefs()),
            'evidence_count': len(self._evidence_history),
            'strongest_beliefs': sorted(
                [(c, b.mean) for c, b in self.beliefs.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }