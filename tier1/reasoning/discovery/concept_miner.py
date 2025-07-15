"""
Concept Miner for extracting reusable proof strategies from successful traces.

This module bridges the symbolic reasoning world of theorem proving with the
geometric knowledge representation of RegionAI by mining successful proof
traces and projecting them as concepts in the knowledge graph.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from datetime import datetime

from sentence_transformers import SentenceTransformer

from tier1.knowledge.infrastructure.reasoning_graph import Heuristic, ReasoningType
from tier1.knowledge.infrastructure.hub_v1 import KnowledgeHub


logger = logging.getLogger(__name__)


class ConceptMiner:
    """
    Mines successful proof traces to extract reusable proof strategies.
    
    This service analyzes proof traces, identifies successful tactic sequences,
    and projects them as new transformation concepts into the geometric
    knowledge graph, enabling the system to learn from its successes.
    """
    
    def __init__(self, 
                 hub: KnowledgeHub,
                 traces_dir: Optional[Path] = None,
                 nlp_model: Optional[SentenceTransformer] = None):
        """
        Initialize the Concept Miner.
        
        Args:
            hub: The KnowledgeHub for accessing and updating knowledge graphs
            traces_dir: Directory containing proof trace files (.jsonl)
            nlp_model: Sentence transformer for vectorizing concept descriptions
        """
        self.hub = hub
        self.traces_dir = traces_dir or Path("traces")
        
        # Initialize NLP model for vectorization
        if nlp_model is None:
            logger.info("Loading sentence transformer for concept vectorization")
            self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.nlp_model = nlp_model
        
        # Track mined concepts to avoid duplicates
        self.mined_concepts: Set[str] = set()
        
    def mine_from_traces(self) -> List[Heuristic]:
        """
        Mine concepts from all available proof traces.
        
        Returns:
            List of new Heuristic concepts discovered
        """
        logger.info(f"Mining concepts from traces in {self.traces_dir}")
        
        if not self.traces_dir.exists():
            logger.warning(f"Traces directory {self.traces_dir} does not exist")
            return []
        
        # Collect all successful proof traces
        successful_traces = self._collect_successful_traces()
        
        if not successful_traces:
            logger.info("No successful traces found to mine")
            return []
        
        logger.info(f"Found {len(successful_traces)} successful proof traces")
        
        # Extract and cluster similar tactic sequences
        tactic_patterns = self._extract_tactic_patterns(successful_traces)
        
        # Convert patterns to transformation concepts
        new_concepts = []
        for pattern, instances in tactic_patterns.items():
            if pattern in self.mined_concepts:
                continue
                
            concept = self._create_transformation_concept(pattern, instances)
            if concept:
                new_concepts.append(concept)
                self.mined_concepts.add(pattern)
        
        # Add concepts to knowledge graphs
        if new_concepts:
            self._integrate_concepts(new_concepts)
            
        logger.info(f"Mined {len(new_concepts)} new concepts from traces")
        return new_concepts
    
    def _collect_successful_traces(self) -> List[Dict[str, Any]]:
        """Collect all successful proof traces from trace files."""
        successful_traces = []
        
        for trace_file in self.traces_dir.glob("*.jsonl"):
            try:
                with open(trace_file, 'r') as f:
                    # Read all events from the trace
                    events = []
                    for line in f:
                        if line.strip():
                            try:
                                event = json.loads(line)
                                events.append(event)
                            except json.JSONDecodeError:
                                continue
                    
                    # Check if this trace represents a successful proof
                    trace_data = self._parse_trace_events(events)
                    if trace_data and trace_data.get('success'):
                        trace_data['trace_file'] = trace_file.name
                        successful_traces.append(trace_data)
                        
            except Exception as e:
                logger.error(f"Error reading trace file {trace_file}: {e}")
                
        return successful_traces
    
    def _parse_trace_events(self, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse a sequence of trace events to extract proof information."""
        trace_data = {
            'theorem_name': None,
            'theorem_statement': None,
            'tactic_sequence': [],
            'success': False,
            'total_steps': 0
        }
        
        for event in events:
            event_type = event.get('event_type', '')
            data = event.get('data', {})
            
            if event_type == 'theorem_start':
                trace_data['theorem_name'] = data.get('name')
                trace_data['theorem_statement'] = data.get('statement')
                
            elif event_type == 'tactic_apply':
                tactic_info = {
                    'tactic': data.get('tactic'),
                    'tactic_type': data.get('tactic_type'),
                    'arguments': data.get('arguments', [])
                }
                trace_data['tactic_sequence'].append(tactic_info)
                
            elif event_type == 'proof_complete':
                trace_data['success'] = data.get('success', False)
                trace_data['total_steps'] = data.get('steps', 0)
        
        # Only return if we have meaningful data
        if trace_data['theorem_name'] and trace_data['tactic_sequence']:
            return trace_data
        return None
    
    def _extract_tactic_patterns(self, traces: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract and group similar tactic sequences.
        
        Returns a dictionary mapping pattern strings to lists of trace instances.
        """
        patterns = defaultdict(list)
        
        for trace in traces:
            # Create a normalized pattern string from the tactic sequence
            pattern = self._normalize_tactic_sequence(trace['tactic_sequence'])
            
            if pattern:  # Only consider non-empty patterns
                patterns[pattern].append(trace)
        
        # Filter patterns that appear multiple times or are particularly interesting
        filtered_patterns = {}
        for pattern, instances in patterns.items():
            # Keep patterns that appear multiple times or have short, elegant sequences
            tactic_count = len(instances[0]['tactic_sequence'])
            if len(instances) >= 2 or (tactic_count <= 4 and len(instances) >= 1):
                filtered_patterns[pattern] = instances
                
        return filtered_patterns
    
    def _normalize_tactic_sequence(self, tactics: List[Dict[str, Any]]) -> str:
        """
        Create a normalized string representation of a tactic sequence.
        
        This allows us to identify similar patterns even with different
        variable names or minor variations.
        """
        normalized_parts = []
        
        for tactic in tactics:
            tactic_str = tactic.get('tactic', '')
            tactic_type = tactic.get('tactic_type', '')
            
            # Normalize the tactic representation
            if tactic_type == 'intro':
                # For intro, just record that we did an intro (ignore variable name)
                normalized_parts.append('intro <var>')
            elif tactic_type == 'exact':
                # For exact, try to identify if it's using a hypothesis
                if any(arg in tactic_str for arg in ['h', 'h1', 'h2']):
                    normalized_parts.append('exact <hyp>')
                else:
                    normalized_parts.append('exact <expr>')
            elif tactic_type == 'apply':
                normalized_parts.append('apply <term>')
            else:
                # For other tactics, use the tactic type
                normalized_parts.append(tactic_type or tactic_str.split()[0])
        
        return '; '.join(normalized_parts)
    
    def _create_transformation_concept(self, 
                                     pattern: str, 
                                     instances: List[Dict[str, Any]]) -> Optional[Heuristic]:
        """
        Create a new Heuristic concept from a tactic pattern.
        
        This is where we bridge the symbolic and geometric worlds.
        """
        # Generate a human-readable description
        description = self._generate_pattern_description(pattern, instances)
        
        if not description:
            return None
        
        # Create a unique name for this concept
        concept_name = f"proof_pattern_{hash(pattern) % 10000:04d}"
        
        # Vectorize the description to get geometric representation
        logger.debug(f"Vectorizing concept: {description}")
        vector = self.nlp_model.encode(description)
        
        # Extract metadata from instances
        example_theorems = [inst['theorem_name'] for inst in instances[:3]]
        avg_steps = sum(inst['total_steps'] for inst in instances) / len(instances)
        
        # Create the heuristic
        # Encode the pattern in the description for the Planner to find
        full_description = f"{description} [Pattern: {pattern}]"
        
        heuristic = Heuristic(
            name=concept_name,
            reasoning_type=ReasoningType.HEURISTIC,
            description=full_description,
            applicability_conditions=tuple([pattern]),  # Use pattern as condition
            expected_utility=0.8,  # Default utility for discovered patterns
            implementation_id=f"mined_{concept_name}"
        )
        
        # Store metadata separately when adding to knowledge graph
        self.metadata_for_heuristic = {
            'pattern': pattern,
            'example_theorems': example_theorems,
            'instance_count': len(instances),
            'average_steps': avg_steps,
            'discovered_date': datetime.now().isoformat(),
            'source': 'concept_miner',
            'vector_representation': vector.tolist()
        }
        
        logger.info(f"Created concept '{concept_name}': {description}")
        return heuristic
    
    def _generate_pattern_description(self, pattern: str, instances: List[Dict[str, Any]]) -> str:
        """
        Generate a natural language description of a proof pattern.
        
        This description will be vectorized to place the concept in geometric space.
        """
        tactics = pattern.split('; ')
        
        # Analyze the pattern to generate a meaningful description
        if len(tactics) == 1:
            if tactics[0] == 'intro <var>':
                return "Prove implication by introducing hypothesis"
            elif tactics[0] == 'exact <hyp>':
                return "Prove goal by exact hypothesis match"
            elif tactics[0] == 'assumption':
                return "Prove goal by finding matching assumption"
                
        elif len(tactics) == 2:
            if tactics[0] == 'intro <var>' and tactics[1] == 'exact <hyp>':
                return "Prove goal by introducing and immediately using hypothesis"
            elif tactics[0] == 'intro <var>' and tactics[1] == 'apply <term>':
                return "Prove goal by introducing hypothesis and applying it"
            elif tactics[0] == 'split' and tactics[1] == 'exact <hyp>':
                return "Prove conjunction by splitting and using hypotheses"
                
        elif len(tactics) == 3:
            if all('intro' in t for t in tactics[:2]):
                return "Prove nested implication by multiple introductions"
            elif 'split' in tactics[0]:
                return "Prove conjunction by splitting into subgoals"
                
        elif len(tactics) == 4:
            if tactics[0] == 'split' and all('exact' in t for t in tactics[1:3]):
                return "Prove conjunction by splitting and proving each part"
                
        # Fallback: create a generic description
        tactic_types = [t.split()[0] for t in tactics]
        return f"Prove goal using sequence: {' then '.join(tactic_types)}"
    
    def _integrate_concepts(self, concepts: List[Heuristic]):
        """Add the mined concepts to the knowledge graphs."""
        wkg = self.hub.wkg  # Use correct attribute name
        rkg = self.hub.rkg  # Use correct attribute name
        
        for heuristic in concepts:
            # Add to reasoning knowledge graph with metadata
            from tier1.knowledge.infrastructure.reasoning_graph import ReasoningMetadata
            metadata = ReasoningMetadata(
                discovery_source='concept_miner',
                context_tags=['proof_pattern', 'learned']
            )
            rkg.add_concept(heuristic, metadata)
            
            logger.debug(f"Added heuristic {heuristic.name} to reasoning knowledge graph")
    
    def generate_report(self, new_concepts: List[Heuristic]) -> str:
        """Generate a summary report of mined concepts."""
        if not new_concepts:
            return "\n--- Concept Miner Report ---\nNo new concepts mined in this run.\n"
        
        report_lines = [
            "\n--- Concept Miner Report ---",
            f"Mined {len(new_concepts)} new concepts from successful proofs.",
            "New Concepts Added:"
        ]
        
        for concept in new_concepts:
            # Extract pattern from description
            pattern = 'unknown'
            if '[Pattern: ' in concept.description:
                pattern = concept.description.split('[Pattern: ', 1)[1].rstrip(']')
            
            report_lines.append(
                f"  - [Concept: {concept.name}]"
            )
            report_lines.append(f"    Description: {concept.description}")
            report_lines.append(f"    Utility: {concept.expected_utility}")
        
        report_lines.append("")
        return '\n'.join(report_lines)