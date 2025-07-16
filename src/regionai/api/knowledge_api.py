"""
Knowledge API - Public facade for knowledge management and querying.

This module provides a clean API for managing and querying the
knowledge graph and reasoning capabilities.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
import logging
from datetime import datetime

# Import from new structure
from ..brains.bayesian import BayesianBrain
from ..brains.logic import LogicBrain
from ..brains.temporal import TemporalBrain
from ..domains.commonsense.primitives import CommonSensePrimitives

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeQuery:
    """Represents a knowledge query."""
    query_type: str  # "fact", "relation", "inference", "temporal", "commonsense"
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    
@dataclass
class KnowledgeResult:
    """Result from a knowledge operation."""
    success: bool
    query: KnowledgeQuery
    results: List[Dict[str, Any]]
    confidence: float
    reasoning_path: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    

@dataclass 
class KnowledgeFact:
    """Represents a fact in the knowledge base."""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = "direct"
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeAPI:
    """
    Public API for knowledge management and reasoning.
    
    This class provides methods for adding facts, querying knowledge,
    and performing inference.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Knowledge API.
        
        Args:
            config: Optional configuration
        """
        self.config = config or {}
        
        # Initialize cognitive modules
        self.bayesian_brain = BayesianBrain()
        self.logic_brain = LogicBrain()
        self.temporal_brain = TemporalBrain()
        self.commonsense = CommonSensePrimitives()
        
        # Knowledge storage
        self.facts: List[KnowledgeFact] = []
        self.relations: Dict[str, List[Tuple[str, str]]] = {}
        
    def add_fact(self, subject: str, predicate: str, object: str,
                confidence: float = 1.0, source: str = "user") -> bool:
        """
        Add a fact to the knowledge base.
        
        Args:
            subject: Subject of the fact
            predicate: Relationship/property
            object: Object of the fact
            confidence: Confidence level [0, 1]
            source: Source of the fact
            
        Returns:
            Success status
        """
        fact = KnowledgeFact(
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            source=source,
            timestamp=datetime.now()
        )
        
        self.facts.append(fact)
        
        # Update Bayesian beliefs
        self.bayesian_brain.observe_relationship(
            subject, predicate, object, True, confidence
        )
        
        # Add to logic brain as statement
        statement_id = f"{subject}_{predicate}_{object}"
        self.logic_brain.add_statement(
            statement_id,
            f"{subject} {predicate} {object}"
        )
        
        # Track temporal aspect
        self.temporal_brain.record_event(
            f"fact_added_{len(self.facts)}",
            f"Added: {subject} {predicate} {object}"
        )
        
        logger.info(f"Added fact: {subject} {predicate} {object}")
        return True
        
    def query(self, query_type: str, **kwargs) -> KnowledgeResult:
        """
        Query the knowledge base.
        
        Args:
            query_type: Type of query ("fact", "relation", "inference", etc.)
            **kwargs: Query parameters
            
        Returns:
            Query results
        """
        query = KnowledgeQuery(
            query_type=query_type,
            subject=kwargs.get("subject"),
            predicate=kwargs.get("predicate"),
            object=kwargs.get("object"),
            constraints=kwargs.get("constraints", {})
        )
        
        if query_type == "fact":
            return self._query_facts(query)
        elif query_type == "relation":
            return self._query_relations(query)
        elif query_type == "inference":
            return self._query_inference(query)
        elif query_type == "temporal":
            return self._query_temporal(query)
        elif query_type == "commonsense":
            return self._query_commonsense(query)
        else:
            return KnowledgeResult(
                success=False,
                query=query,
                results=[],
                confidence=0.0,
                reasoning_path=[f"Unknown query type: {query_type}"]
            )
            
    def reason(self, goal: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform reasoning to achieve a goal.
        
        Args:
            goal: Goal to achieve
            constraints: Optional constraints
            
        Returns:
            Reasoning results
        """
        logger.info(f"Reasoning towards goal: {goal}")
        
        # Parse goal
        goal_parts = goal.split()
        
        # Try logical reasoning first
        logic_result = self._reason_logically(goal, constraints)
        
        # Get Bayesian perspective
        bayesian_result = self._reason_probabilistically(goal, constraints)
        
        # Consider temporal aspects
        temporal_result = self._reason_temporally(goal, constraints)
        
        # Combine results
        combined_confidence = self._combine_reasoning_results(
            logic_result, bayesian_result, temporal_result
        )
        
        return {
            "goal": goal,
            "achievable": combined_confidence > 0.5,
            "confidence": combined_confidence,
            "logical_path": logic_result.get("path", []),
            "probabilistic_assessment": bayesian_result,
            "temporal_considerations": temporal_result,
            "recommendations": self._generate_recommendations(
                goal, combined_confidence, constraints
            )
        }
        
    def explain(self, fact_or_query: Union[str, KnowledgeFact]) -> Dict[str, Any]:
        """
        Explain how a fact was derived or why a query returned certain results.
        
        Args:
            fact_or_query: Fact or query to explain
            
        Returns:
            Explanation
        """
        if isinstance(fact_or_query, str):
            # Parse as fact
            parts = fact_or_query.split()
            if len(parts) >= 3:
                subject, predicate = parts[0], parts[1]
                object = " ".join(parts[2:])
            else:
                return {"error": "Invalid fact format"}
        else:
            subject = fact_or_query.subject
            predicate = fact_or_query.predicate
            object = fact_or_query.object
            
        # Find the fact
        matching_facts = [
            f for f in self.facts
            if f.subject == subject and f.predicate == predicate and f.object == object
        ]
        
        if not matching_facts:
            return {"error": "Fact not found"}
            
        fact = matching_facts[0]
        
        # Generate explanation
        explanation = {
            "fact": f"{subject} {predicate} {object}",
            "source": fact.source,
            "confidence": fact.confidence,
            "added_at": fact.timestamp.isoformat() if fact.timestamp else "unknown",
            "reasoning": []
        }
        
        # Check if derived through inference
        statement_id = f"{subject}_{predicate}_{object}"
        if statement_id in self.logic_brain.statements:
            proof_steps = self.logic_brain.explain_proof(statement_id)
            explanation["reasoning"].extend(proof_steps)
            
        # Add Bayesian perspective
        belief = self.bayesian_brain.query_relationship(subject, predicate, object)
        if belief is not None:
            explanation["bayesian_belief"] = belief
            belief_explanation = self.bayesian_brain.explain_belief(
                f"{subject}_{predicate}_{object}"
            )
            explanation["belief_basis"] = belief_explanation
            
        # Add temporal context
        temporal_explanation = self.temporal_brain.explain_timing(
            f"fact_{subject}_{predicate}_{object}"
        )
        if "error" not in temporal_explanation:
            explanation["temporal_context"] = temporal_explanation
            
        return explanation
        
    def learn_from_text(self, text: str, source: str = "text") -> Dict[str, Any]:
        """
        Extract and learn facts from natural language text.
        
        Args:
            text: Natural language text
            source: Source identifier
            
        Returns:
            Learning results
        """
        # Apply commonsense understanding
        commonsense_analysis = self.commonsense.apply_to_scenario(text)
        
        # Extract facts (simplified - real system would use NLP)
        extracted_facts = self._extract_facts_from_text(text)
        
        # Add facts to knowledge base
        added_facts = []
        for fact in extracted_facts:
            success = self.add_fact(
                fact["subject"],
                fact["predicate"], 
                fact["object"],
                confidence=fact.get("confidence", 0.8),
                source=source
            )
            if success:
                added_facts.append(fact)
                
        return {
            "text_length": len(text),
            "facts_extracted": len(extracted_facts),
            "facts_added": len(added_facts),
            "commonsense_concepts": commonsense_analysis.get("primitives", []),
            "added_facts": added_facts
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        # Collect stats from all brains
        bayesian_summary = self.bayesian_brain.get_summary()
        logic_consistency = self.logic_brain.check_consistency()
        
        # Count facts by predicate
        predicate_counts = {}
        for fact in self.facts:
            predicate_counts[fact.predicate] = predicate_counts.get(fact.predicate, 0) + 1
            
        return {
            "total_facts": len(self.facts),
            "unique_subjects": len(set(f.subject for f in self.facts)),
            "unique_predicates": len(predicate_counts),
            "unique_objects": len(set(f.object for f in self.facts)),
            "predicate_distribution": predicate_counts,
            "bayesian_beliefs": bayesian_summary["total_concepts"],
            "logical_statements": logic_consistency["total_statements"],
            "proven_statements": logic_consistency["proven_statements"],
            "contradictions": len(logic_consistency["contradictions"]),
            "temporal_events": len(self.temporal_brain.events),
            "sources": list(set(f.source for f in self.facts))
        }
        
    def export_knowledge(self, format: str = "json") -> Union[Dict[str, Any], str]:
        """
        Export knowledge base.
        
        Args:
            format: Export format ("json", "rdf", "text")
            
        Returns:
            Exported knowledge
        """
        if format == "json":
            return {
                "facts": [
                    {
                        "subject": f.subject,
                        "predicate": f.predicate,
                        "object": f.object,
                        "confidence": f.confidence,
                        "source": f.source,
                        "timestamp": f.timestamp.isoformat() if f.timestamp else None
                    }
                    for f in self.facts
                ],
                "statistics": self.get_statistics()
            }
        elif format == "text":
            lines = []
            for fact in self.facts:
                lines.append(
                    f"{fact.subject} {fact.predicate} {fact.object} "
                    f"(confidence: {fact.confidence:.2f}, source: {fact.source})"
                )
            return "\n".join(lines)
        elif format == "rdf":
            # Simplified RDF-like format
            lines = []
            for fact in self.facts:
                lines.append(
                    f"<{fact.subject}> <{fact.predicate}> <{fact.object}> ."
                )
            return "\n".join(lines)
        else:
            return {"error": f"Unsupported format: {format}"}
            
    def _query_facts(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Query direct facts."""
        results = []
        
        for fact in self.facts:
            # Check if fact matches query
            if (query.subject is None or fact.subject == query.subject) and \
               (query.predicate is None or fact.predicate == query.predicate) and \
               (query.object is None or fact.object == query.object):
                
                # Apply additional constraints
                if self._check_constraints(fact, query.constraints):
                    results.append({
                        "subject": fact.subject,
                        "predicate": fact.predicate,
                        "object": fact.object,
                        "confidence": fact.confidence,
                        "source": fact.source
                    })
                    
        return KnowledgeResult(
            success=len(results) > 0,
            query=query,
            results=results,
            confidence=max([r["confidence"] for r in results]) if results else 0.0,
            sources=list(set(r["source"] for r in results))
        )
        
    def _query_relations(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Query relationships."""
        # Use Bayesian brain for relationship queries
        results = []
        
        if query.subject and query.predicate:
            # Find all objects related to subject via predicate
            for fact in self.facts:
                if fact.subject == query.subject and fact.predicate == query.predicate:
                    belief = self.bayesian_brain.query_relationship(
                        fact.subject, fact.predicate, fact.object
                    )
                    if belief and belief > 0.5:
                        results.append({
                            "subject": fact.subject,
                            "predicate": fact.predicate,
                            "object": fact.object,
                            "belief": belief
                        })
                        
        return KnowledgeResult(
            success=len(results) > 0,
            query=query,
            results=results,
            confidence=max([r["belief"] for r in results]) if results else 0.0
        )
        
    def _query_inference(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Query using inference."""
        # Use logic brain for inference
        results = []
        reasoning_path = []
        
        # Create goal statement
        if query.subject and query.predicate and query.object:
            goal = f"{query.subject} {query.predicate} {query.object}"
            statement_id = f"{query.subject}_{query.predicate}_{query.object}"
            
            # Try to prove
            if self.logic_brain.prove(statement_id):
                results.append({
                    "proven": True,
                    "statement": goal
                })
                reasoning_path = self.logic_brain.explain_proof(statement_id)
                confidence = 1.0
            else:
                confidence = 0.0
        else:
            confidence = 0.0
            
        return KnowledgeResult(
            success=len(results) > 0,
            query=query,
            results=results,
            confidence=confidence,
            reasoning_path=reasoning_path
        )
        
    def _query_temporal(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Query temporal relationships."""
        # Use temporal brain
        results = []
        
        if "time_range" in query.constraints:
            # Query events in time range
            start_time = query.constraints["time_range"][0]
            end_time = query.constraints["time_range"][1]
            
            for event_id, event in self.temporal_brain.events.items():
                if start_time <= event.start_time <= end_time:
                    results.append({
                        "event": event.description,
                        "time": event.start_time,
                        "duration": event.duration
                    })
                    
        return KnowledgeResult(
            success=len(results) > 0,
            query=query,
            results=results,
            confidence=1.0 if results else 0.0
        )
        
    def _query_commonsense(self, query: KnowledgeQuery) -> KnowledgeResult:
        """Query using commonsense reasoning."""
        results = []
        
        if query.subject:
            # Apply commonsense to understand the query
            analysis = self.commonsense.apply_to_scenario(query.subject)
            
            if "primitives" in analysis:
                for primitive in analysis["primitives"]:
                    prim_obj = self.commonsense.get_primitive(primitive)
                    if prim_obj:
                        results.append({
                            "concept": primitive,
                            "category": prim_obj.category.value,
                            "properties": prim_obj.properties,
                            "examples": prim_obj.examples[:2]
                        })
                        
        return KnowledgeResult(
            success=len(results) > 0,
            query=query,
            results=results,
            confidence=0.8 if results else 0.0  # Commonsense has inherent uncertainty
        )
        
    def _check_constraints(self, fact: KnowledgeFact,
                         constraints: Dict[str, Any]) -> bool:
        """Check if fact satisfies constraints."""
        for key, value in constraints.items():
            if key == "min_confidence" and fact.confidence < value:
                return False
            elif key == "source" and fact.source != value:
                return False
            elif key == "after" and fact.timestamp and fact.timestamp < value:
                return False
            elif key == "before" and fact.timestamp and fact.timestamp > value:
                return False
                
        return True
        
    def _reason_logically(self, goal: str,
                        constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform logical reasoning."""
        # Try to prove the goal
        goal_id = goal.replace(" ", "_")
        
        if self.logic_brain.prove(goal_id, max_steps=50):
            return {
                "success": True,
                "path": self.logic_brain.explain_proof(goal_id),
                "confidence": 1.0
            }
        else:
            return {
                "success": False,
                "path": [],
                "confidence": 0.0
            }
            
    def _reason_probabilistically(self, goal: str,
                                constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform probabilistic reasoning."""
        # Use Bayesian brain
        belief = self.bayesian_brain.query_belief(goal)
        
        if belief is None:
            # Try to infer from related concepts
            confident_beliefs = self.bayesian_brain.get_confident_beliefs(0.6)
            related = [b for b in confident_beliefs if goal.split()[0] in b]
            
            if related:
                # Average belief in related concepts
                belief = sum(confident_beliefs[r] for r in related) / len(related)
            else:
                belief = 0.5  # Unknown
                
        return {
            "belief": belief,
            "confidence": self.bayesian_brain.assess_confidence("bayesian", goal),
            "explanation": self.bayesian_brain.explain_belief(goal)
        }
        
    def _reason_temporally(self, goal: str,
                         constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Consider temporal aspects of reasoning."""
        # Check if goal involves temporal concepts
        temporal_keywords = ["before", "after", "during", "when", "until"]
        
        has_temporal = any(keyword in goal.lower() for keyword in temporal_keywords)
        
        if has_temporal:
            # Analyze temporal relationships
            # Simplified - real system would parse temporal logic
            return {
                "has_temporal_aspect": True,
                "feasibility": "requires temporal planning",
                "suggested_approach": "break into temporal steps"
            }
        else:
            return {
                "has_temporal_aspect": False,
                "feasibility": "no temporal constraints"
            }
            
    def _combine_reasoning_results(self, logic_result: Dict[str, Any],
                                 bayesian_result: Dict[str, Any],
                                 temporal_result: Dict[str, Any]) -> float:
        """Combine results from different reasoning approaches."""
        # Weighted combination
        weights = {
            "logic": 0.4,
            "bayesian": 0.4,
            "temporal": 0.2
        }
        
        combined = 0.0
        
        if logic_result.get("success"):
            combined += weights["logic"] * logic_result.get("confidence", 1.0)
        
        combined += weights["bayesian"] * bayesian_result.get("belief", 0.5)
        
        if temporal_result.get("has_temporal_aspect"):
            # Temporal aspects add uncertainty
            combined *= 0.8
            
        return combined
        
    def _generate_recommendations(self, goal: str, confidence: float,
                                constraints: Optional[Dict[str, Any]]) -> List[str]:
        """Generate recommendations for achieving goal."""
        recommendations = []
        
        if confidence < 0.3:
            recommendations.append("Goal appears difficult to achieve with current knowledge")
            recommendations.append("Consider gathering more information")
        elif confidence < 0.7:
            recommendations.append("Goal is potentially achievable")
            recommendations.append("Recommend validating key assumptions")
        else:
            recommendations.append("Goal appears achievable with high confidence")
            
        if constraints:
            recommendations.append(f"Note constraints: {list(constraints.keys())}")
            
        return recommendations
        
    def _extract_facts_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract facts from text (simplified)."""
        # Very simplified extraction
        # Real system would use NLP
        
        facts = []
        
        # Look for simple patterns like "X is Y"
        import re
        
        # Pattern: "X is Y"
        is_pattern = re.compile(r'(\w+)\s+is\s+(\w+)')
        for match in is_pattern.finditer(text):
            facts.append({
                "subject": match.group(1),
                "predicate": "is",
                "object": match.group(2),
                "confidence": 0.7
            })
            
        # Pattern: "X has Y"
        has_pattern = re.compile(r'(\w+)\s+has\s+(\w+)')
        for match in has_pattern.finditer(text):
            facts.append({
                "subject": match.group(1),
                "predicate": "has",
                "object": match.group(2),
                "confidence": 0.7
            })
            
        return facts


# Convenience functions
def add_fact(subject: str, predicate: str, object: str, **kwargs) -> bool:
    """Quick fact addition."""
    api = KnowledgeAPI()
    return api.add_fact(subject, predicate, object, **kwargs)


def query(query_type: str, **kwargs) -> KnowledgeResult:
    """Quick query."""
    api = KnowledgeAPI()
    return api.query(query_type, **kwargs)


def reason(goal: str, **kwargs) -> Dict[str, Any]:
    """Quick reasoning."""
    api = KnowledgeAPI()
    return api.reason(goal, **kwargs)