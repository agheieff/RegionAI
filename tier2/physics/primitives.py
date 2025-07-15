"""
Commonsense Primitives - Basic building blocks of everyday reasoning.

This module defines primitive concepts and relationships that form
the foundation of commonsense reasoning.
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CommonSenseCategory(Enum):
    """Categories of commonsense knowledge."""
    PHYSICAL = "physical"  # Physical properties and laws
    SOCIAL = "social"      # Social norms and interactions
    TEMPORAL = "temporal"  # Time-related concepts
    SPATIAL = "spatial"    # Space and location
    CAUSAL = "causal"      # Cause and effect
    FUNCTIONAL = "functional"  # Object functions and purposes


@dataclass
class CommonSensePrimitive:
    """A primitive commonsense concept."""
    name: str
    category: CommonSenseCategory
    properties: Dict[str, Any]
    relations: Dict[str, List[str]]  # relation_type -> [related_concepts]
    constraints: List[str]
    examples: List[str]


class CommonSensePrimitives:
    """
    Repository of commonsense primitive concepts.
    
    These primitives serve as building blocks for more complex reasoning
    about everyday situations and objects.
    """
    
    def __init__(self):
        self.primitives: Dict[str, CommonSensePrimitive] = {}
        self._initialize_primitives()
        
    def _initialize_primitives(self):
        """Initialize basic commonsense primitives."""
        
        # Physical primitives
        self.add_primitive(
            "gravity",
            CommonSenseCategory.PHYSICAL,
            properties={"direction": "down", "universal": True},
            relations={"affects": ["objects", "liquids"], "causes": ["falling"]},
            constraints=["Objects fall down unless supported"],
            examples=["Dropped items fall to the ground", "Water flows downhill"]
        )
        
        self.add_primitive(
            "container",
            CommonSenseCategory.FUNCTIONAL,
            properties={"can_hold": True, "has_interior": True},
            relations={"contains": ["objects", "liquids"], "has_property": ["volume", "opening"]},
            constraints=["Cannot hold more than capacity", "Must have opening to insert items"],
            examples=["Cup holds water", "Box contains items"]
        )
        
        # Social primitives
        self.add_primitive(
            "ownership",
            CommonSenseCategory.SOCIAL,
            properties={"exclusive": True, "transferable": True},
            relations={"belongs_to": ["person"], "applies_to": ["objects"]},
            constraints=["One owner at a time", "Owner has usage rights"],
            examples=["My car", "Her book"]
        )
        
        self.add_primitive(
            "politeness",
            CommonSenseCategory.SOCIAL,
            properties={"context_dependent": True, "cultural": True},
            relations={"expressed_by": ["words", "actions"], "expected_in": ["interactions"]},
            constraints=["Varies by culture", "Required in formal settings"],
            examples=["Saying please", "Holding door open"]
        )
        
        # Temporal primitives
        self.add_primitive(
            "before_after",
            CommonSenseCategory.TEMPORAL,
            properties={"transitive": True, "irreflexive": True},
            relations={"orders": ["events"], "determines": ["sequence"]},
            constraints=["If A before B and B before C, then A before C"],
            examples=["Breakfast before lunch", "Cause before effect"]
        )
        
        self.add_primitive(
            "duration",
            CommonSenseCategory.TEMPORAL,
            properties={"measurable": True, "additive": True},
            relations={"property_of": ["events", "processes"], "measured_in": ["time_units"]},
            constraints=["Non-negative", "Finite for completed events"],
            examples=["Meeting lasts 1 hour", "Cooking takes 30 minutes"]
        )
        
        # Spatial primitives
        self.add_primitive(
            "inside_outside",
            CommonSenseCategory.SPATIAL,
            properties={"binary": True, "relative": True},
            relations={"applies_to": ["containers", "boundaries"], "opposite_of": ["outside", "inside"]},
            constraints=["Cannot be both simultaneously", "Requires boundary"],
            examples=["Cat inside house", "Car outside garage"]
        )
        
        self.add_primitive(
            "distance",
            CommonSenseCategory.SPATIAL,
            properties={"metric": True, "symmetric": True},
            relations={"between": ["objects", "locations"], "affects": ["reachability", "travel_time"]},
            constraints=["Non-negative", "Triangle inequality"],
            examples=["Store is 2 miles away", "Reach requires proximity"]
        )
        
        # Causal primitives
        self.add_primitive(
            "cause_effect",
            CommonSenseCategory.CAUSAL,
            properties={"directional": True, "temporal": True},
            relations={"links": ["events"], "requires": ["temporal_precedence"]},
            constraints=["Cause precedes effect", "Effect depends on cause"],
            examples=["Push causes movement", "Heat causes melting"]
        )
        
        self.add_primitive(
            "prevention",
            CommonSenseCategory.CAUSAL,
            properties={"negative_causation": True, "intentional": True},
            relations={"blocks": ["events"], "requires": ["intervention"]},
            constraints=["Must occur before prevented event", "Removes necessary condition"],
            examples=["Umbrella prevents getting wet", "Lock prevents entry"]
        )
        
        # Functional primitives
        self.add_primitive(
            "tool_use",
            CommonSenseCategory.FUNCTIONAL,
            properties={"purposeful": True, "instrumental": True},
            relations={"uses": ["tools"], "achieves": ["goals"], "requires": ["knowledge"]},
            constraints=["Tool must be appropriate", "User must know how"],
            examples=["Hammer for nails", "Key opens lock"]
        )
        
        self.add_primitive(
            "breakability",
            CommonSenseCategory.PHYSICAL,
            properties={"material_dependent": True, "irreversible": True},
            relations={"property_of": ["objects"], "caused_by": ["force", "impact"]},
            constraints=["Fragile items break easier", "Breaking changes function"],
            examples=["Glass shatters", "Egg cracks"]
        )
        
    def add_primitive(self, name: str, category: CommonSenseCategory,
                     properties: Dict[str, Any], relations: Dict[str, List[str]],
                     constraints: List[str], examples: List[str]):
        """Add a new commonsense primitive."""
        self.primitives[name] = CommonSensePrimitive(
            name=name,
            category=category,
            properties=properties,
            relations=relations,
            constraints=constraints,
            examples=examples
        )
        
    def get_primitive(self, name: str) -> Optional[CommonSensePrimitive]:
        """Get a primitive by name."""
        return self.primitives.get(name)
        
    def get_by_category(self, category: CommonSenseCategory) -> List[CommonSensePrimitive]:
        """Get all primitives in a category."""
        return [p for p in self.primitives.values() if p.category == category]
        
    def find_related(self, primitive_name: str, relation_type: str) -> List[str]:
        """Find concepts related to a primitive."""
        primitive = self.get_primitive(primitive_name)
        if primitive and relation_type in primitive.relations:
            return primitive.relations[relation_type]
        return []
        
    def check_constraint(self, primitive_name: str, situation: Dict[str, Any]) -> List[str]:
        """
        Check which constraints of a primitive apply to a situation.
        
        Returns:
            List of applicable constraints
        """
        primitive = self.get_primitive(primitive_name)
        if not primitive:
            return []
            
        # This is a simple implementation - in practice would need
        # more sophisticated constraint checking
        applicable = []
        for constraint in primitive.constraints:
            # Check if any key terms from constraint appear in situation
            if any(term.lower() in str(situation).lower() 
                  for term in constraint.split()):
                applicable.append(constraint)
                
        return applicable
        
    def compose_primitives(self, primitives: List[str]) -> Dict[str, Any]:
        """
        Compose multiple primitives to understand complex situations.
        
        Args:
            primitives: List of primitive names to compose
            
        Returns:
            Composed understanding
        """
        if not primitives:
            return {}
            
        composed = {
            'primitives': primitives,
            'categories': set(),
            'all_properties': {},
            'all_relations': {},
            'all_constraints': [],
            'interactions': []
        }
        
        # Gather all properties and relations
        for prim_name in primitives:
            prim = self.get_primitive(prim_name)
            if prim:
                composed['categories'].add(prim.category.value)
                composed['all_properties'].update(prim.properties)
                
                for rel_type, related in prim.relations.items():
                    if rel_type not in composed['all_relations']:
                        composed['all_relations'][rel_type] = []
                    composed['all_relations'][rel_type].extend(related)
                    
                composed['all_constraints'].extend(prim.constraints)
                
        # Find interactions between primitives
        for i, prim1_name in enumerate(primitives):
            for prim2_name in primitives[i+1:]:
                interaction = self._find_interaction(prim1_name, prim2_name)
                if interaction:
                    composed['interactions'].append(interaction)
                    
        return composed
        
    def _find_interaction(self, prim1_name: str, prim2_name: str) -> Optional[Dict[str, Any]]:
        """Find potential interaction between two primitives."""
        prim1 = self.get_primitive(prim1_name)
        prim2 = self.get_primitive(prim2_name)
        
        if not prim1 or not prim2:
            return None
            
        # Check for shared relations or properties
        shared_relations = set(prim1.relations.keys()) & set(prim2.relations.keys())
        
        if shared_relations:
            return {
                'type': 'shared_relations',
                'primitives': [prim1_name, prim2_name],
                'shared': list(shared_relations)
            }
            
        # Check if one affects the other
        for rel_type, related in prim1.relations.items():
            if prim2_name in related or prim2.category.value in related:
                return {
                    'type': 'direct_relation',
                    'from': prim1_name,
                    'to': prim2_name,
                    'relation': rel_type
                }
                
        return None
        
    def apply_to_scenario(self, scenario: str) -> Dict[str, Any]:
        """
        Apply commonsense primitives to understand a scenario.
        
        Args:
            scenario: Natural language description
            
        Returns:
            Analysis using primitives
        """
        # Simple keyword matching - in practice would use NLP
        activated_primitives = []
        
        scenario_lower = scenario.lower()
        
        for name, primitive in self.primitives.items():
            # Check if primitive or its examples match
            if name in scenario_lower:
                activated_primitives.append(name)
                continue
                
            # Check examples
            for example in primitive.examples:
                if any(word in scenario_lower for word in example.lower().split()):
                    activated_primitives.append(name)
                    break
                    
        # Compose understanding from activated primitives
        if activated_primitives:
            return self.compose_primitives(activated_primitives)
        else:
            return {'error': 'No matching primitives found'}