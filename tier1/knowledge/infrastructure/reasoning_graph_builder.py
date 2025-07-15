"""
Builder for populating the initial Reasoning Knowledge Graph.

This module is responsible for creating the foundational reasoning concepts
and heuristics that RegionAI uses to discover knowledge from code.
"""
from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph, ReasoningConcept, Heuristic, ReasoningType, Relation, ReasoningMetadata


def populate_initial_reasoning_graph(rkg: ReasoningKnowledgeGraph):
    """
    Populates the ReasoningKnowledgeGraph with the initial set of
    reasoning concepts and heuristics.
    
    This creates nodes for the system's core discovery techniques and
    establishes their relationships.
    """
    # 1. Co-occurrence Analysis
    co_occurrence_concept = ReasoningConcept(
        name="Concept Co-occurrence",
        reasoning_type=ReasoningType.PATTERN,
        description="A reasoning pattern that identifies relationships when concepts appear together in a specific context."
    )
    rkg.add_concept(co_occurrence_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["relationship_discovery", "pattern_recognition"]
    ))
    
    co_occurrence_heuristic = Heuristic(
        name="Co-occurrence in function name implies RELATED_TO",
        reasoning_type=ReasoningType.HEURISTIC,
        description="If two concepts are present in a function's name, they are likely related.",
        utility_model={
            "default": 0.75,
            "api-design": 0.85,  # More useful when analyzing API patterns
            "database-interaction": 0.80  # Useful for finding DB relationships
        },
        implementation_id="pattern.co_occurrence_implies_related"
    )
    rkg.add_concept(co_occurrence_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["relationship_discovery", "name_analysis"]
    ))
    rkg.add_relation(co_occurrence_heuristic, co_occurrence_concept, Relation("IS_A_TYPE_OF"))
    
    # 2. Action Inference
    action_inference_concept = ReasoningConcept(
        name="Action Inference",
        reasoning_type=ReasoningType.PATTERN,
        description="A reasoning pattern that infers actions and their performers from code structures like method calls."
    )
    rkg.add_concept(action_inference_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["action_discovery", "method_analysis"]
    ))
    
    action_heuristic = Heuristic(
        name="Method call implies PERFORMS",
        reasoning_type=ReasoningType.HEURISTIC,
        description="A method call on an object implies the object's class PERFORMS the action represented by the method.",
        utility_model={
            "default": 0.85,
            "object-oriented": 0.95,  # Highly effective in OO code
            "functional": 0.60  # Less useful in functional code
        },
        implementation_id="ast.method_call_implies_performs"
    )
    rkg.add_concept(action_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["action_discovery", "ast_analysis"]
    ))
    rkg.add_relation(action_heuristic, action_inference_concept, Relation("IS_A_TYPE_OF"))
    
    # 3. Sequential Analysis
    sequential_analysis_concept = ReasoningConcept(
        name="Sequential Analysis",
        reasoning_type=ReasoningType.PATTERN,
        description="A reasoning pattern that infers relationships based on the order of appearance in a sequence."
    )
    rkg.add_concept(sequential_analysis_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["temporal_analysis", "sequence_processing"]
    ))
    
    sequence_heuristic = Heuristic(
        name="Sequential AST nodes imply PRECEDES",
        reasoning_type=ReasoningType.HEURISTIC,
        description="If one AST node directly follows another within the same block, a PRECEDES relationship can be inferred.",
        utility_model={
            "default": 0.95,
            "workflow-analysis": 0.99,  # Extremely useful for workflow understanding
            "data-processing": 0.90  # Good for understanding data pipelines
        },
        implementation_id="ast.sequential_nodes_imply_precedes"
    )
    rkg.add_concept(sequence_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["temporal_analysis", "ast_analysis"]
    ))
    rkg.add_relation(sequence_heuristic, sequential_analysis_concept, Relation("IS_A_TYPE_OF"))
    
    # 4. CRUD Pattern Recognition
    crud_concept = ReasoningConcept(
        name="CRUD Pattern Recognition",
        reasoning_type=ReasoningType.PATTERN,
        description="A reasoning pattern that identifies entities through Create, Read, Update, Delete operations."
    )
    rkg.add_concept(crud_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["entity_discovery", "pattern_recognition"]
    ))
    
    crud_heuristic = Heuristic(
        name="CRUD operations identify domain entities",
        reasoning_type=ReasoningType.HEURISTIC,
        description="When functions implement create/read/update/delete for a concept, it's likely a core domain entity.",
        utility_model={
            "default": 0.90,
            "database-interaction": 0.98,  # Extremely useful for DB code
            "api-design": 0.95  # Very useful for REST APIs
        }
    )
    rkg.add_concept(crud_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["entity_discovery", "function_analysis"]
    ))
    rkg.add_relation(crud_heuristic, crud_concept, Relation("IS_A_TYPE_OF"))
    
    # 5. Semantic Relationship Extraction
    semantic_extraction_concept = ReasoningConcept(
        name="Semantic Relationship Extraction",
        reasoning_type=ReasoningType.PATTERN,
        description="A reasoning pattern that extracts relationships from natural language in documentation."
    )
    rkg.add_concept(semantic_extraction_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["nlp", "documentation_analysis"]
    ))
    
    has_many_heuristic = Heuristic(
        name="'has many' phrase implies HAS_MANY relationship",
        reasoning_type=ReasoningType.HEURISTIC,
        description="When documentation mentions 'has many', it indicates a one-to-many relationship.",
        utility_model={
            "default": 0.80,
            "database-interaction": 0.95,  # Critical for ORM understanding
            "domain-modeling": 0.90  # Very useful for domain models
        }
    )
    rkg.add_concept(has_many_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["nlp", "relationship_extraction"]
    ))
    rkg.add_relation(has_many_heuristic, semantic_extraction_concept, Relation("IS_A_TYPE_OF"))
    
    belongs_to_heuristic = Heuristic(
        name="'belongs to' phrase implies BELONGS_TO relationship",
        reasoning_type=ReasoningType.HEURISTIC,
        description="When documentation mentions 'belongs to', it indicates ownership or membership.",
        utility_model={
            "default": 0.80,
            "database-interaction": 0.95,  # Critical for ORM understanding
            "domain-modeling": 0.90  # Very useful for domain models
        }
    )
    rkg.add_concept(belongs_to_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["nlp", "relationship_extraction"]
    ))
    rkg.add_relation(belongs_to_heuristic, semantic_extraction_concept, Relation("IS_A_TYPE_OF"))
    
    # 6. Bayesian Belief Update
    bayesian_concept = ReasoningConcept(
        name="Bayesian Belief Update",
        reasoning_type=ReasoningType.PRINCIPLE,
        description="A fundamental principle for updating beliefs based on evidence."
    )
    rkg.add_concept(bayesian_concept, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["belief_update", "probabilistic_reasoning"]
    ))
    
    evidence_combination_heuristic = Heuristic(
        name="Multiple evidence sources strengthen belief",
        reasoning_type=ReasoningType.HEURISTIC,
        description="When multiple independent sources suggest the same concept or relationship, confidence increases.",
        utility_model={
            "default": 0.85,
            "uncertain-environment": 0.95  # Very useful when evidence is sparse
        }
    )
    rkg.add_concept(evidence_combination_heuristic, ReasoningMetadata(
        discovery_source="built-in",
        context_tags=["belief_update", "evidence_combination"]
    ))
    rkg.add_relation(evidence_combination_heuristic, bayesian_concept, Relation("IS_A_TYPE_OF"))
    
    # Add relationships between high-level concepts
    rkg.add_relation(
        semantic_extraction_concept,
        bayesian_concept,
        Relation("USES"),
        confidence=0.9
    )
    
    rkg.add_relation(
        action_inference_concept,
        sequential_analysis_concept,
        Relation("RELATED_TO"),
        confidence=0.7
    )