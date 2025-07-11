"""
Bayesian Updater service for modifying beliefs in the Knowledge Graph.

This module contains the core logic for taking new evidence and updating
the probabilistic belief distributions (alpha/beta parameters) for
concepts and relationships.
"""
from .graph import KnowledgeGraph, Concept, Relation


class BayesianUpdater:
    """
    Applies Bayesian updates to the beliefs within a KnowledgeGraph.
    """

    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        Initializes the updater with a reference to the graph it will modify.

        Args:
            knowledge_graph: The KnowledgeGraph instance to be updated.
        """
        self.kg = knowledge_graph

    def update_belief(
        self,
        source_concept: Concept,
        target_concept: Concept,
        relation: Relation,
        evidence_is_positive: bool,
        source_credibility: float
    ):
        """
        Updates the belief in a relationship based on new evidence.

        This is the core method for learning. It adjusts the alpha and beta
        parameters of a relationship's belief distribution.

        Args:
            source_concept: The source concept of the relationship.
            target_concept: The target concept of the relationship.
            relation: The type of the relationship.
            evidence_is_positive: True if the evidence supports the relationship,
                                 False if it contradicts it.
            source_credibility: A score from 0.0 to 1.0 representing the
                                trustworthiness of the evidence source.
        """
        # 1. Find the specific edge (relationship) in the graph
        edge_data = self.kg.graph.get_edge_data(source_concept, target_concept)
        
        if edge_data is None:
            # If the relationship doesn't exist, create it with initial priors
            self.kg.add_relation(source_concept, target_concept, relation)
            edge_data = self.kg.graph.get_edge_data(source_concept, target_concept)
        
        # Find the specific edge with the matching relation type
        metadata = None
        for key, data in edge_data.items():
            if data['label'] == relation:
                metadata = data['metadata']
                break
        
        if metadata is None:
            # This shouldn't happen if add_relation worked correctly
            raise ValueError(f"Could not find relationship {source_concept} -> {target_concept} ({relation})")
        
        # 2. Calculate the "strength" of the evidence
        # Base evidence weight of 1.0, multiplied by source credibility
        evidence_strength = 1.0 * source_credibility
        
        # 3. Update alpha or beta based on evidence polarity
        if evidence_is_positive:
            # Positive evidence increases alpha (supporting the relationship)
            metadata.alpha += evidence_strength
        else:
            # Negative evidence increases beta (contradicting the relationship)
            metadata.beta += evidence_strength