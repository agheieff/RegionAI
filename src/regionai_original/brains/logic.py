"""
Logic Brain - "Is it proven?"

This brain module handles formal reasoning, proof verification, and logical inference.
It ensures conclusions are logically sound and tracks proof dependencies.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProofStatus(Enum):
    """Status of a proof or logical statement."""
    PROVEN = "proven"
    DISPROVEN = "disproven"
    UNKNOWN = "unknown"
    ASSUMED = "assumed"
    CONTRADICTORY = "contradictory"


class LogicalConnective(Enum):
    """Logical connectives for building complex statements."""
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"  # If and only if


@dataclass
class LogicalStatement:
    """Represents a logical statement or proposition."""
    id: str
    content: str
    status: ProofStatus = ProofStatus.UNKNOWN
    dependencies: Set[str] = field(default_factory=set)
    proof_steps: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def is_proven(self) -> bool:
        return self.status == ProofStatus.PROVEN
        
    def is_assumable(self) -> bool:
        return self.status in [ProofStatus.UNKNOWN, ProofStatus.ASSUMED]


@dataclass
class ProofStep:
    """A single step in a proof."""
    description: str
    rule_applied: str
    premises: List[str]  # IDs of statements used
    conclusion: str  # ID of statement concluded
    valid: bool = True


@dataclass
class LogicalRule:
    """A rule of inference."""
    name: str
    description: str
    check_applicability: Any  # Function to check if rule applies
    apply: Any  # Function to apply the rule


class LogicBrain:
    """
    The Logic brain handles formal reasoning and proof verification.
    
    Core responsibilities:
    - Track logical statements and their relationships
    - Apply rules of inference
    - Verify proof correctness
    - Detect contradictions
    - Manage assumptions and their consequences
    """
    
    def __init__(self):
        self.statements: Dict[str, LogicalStatement] = {}
        self.rules: Dict[str, LogicalRule] = {}
        self.proof_history: List[ProofStep] = []
        self.assumptions: Set[str] = set()
        self.contradictions: List[Tuple[str, str]] = []
        
        # Initialize basic logical rules
        self._initialize_rules()
        
    def _initialize_rules(self):
        """Set up fundamental rules of inference."""
        # Modus Ponens: P, P→Q ⊢ Q
        self.add_rule(
            "modus_ponens",
            "If P and P→Q are proven, then Q is proven",
            self._check_modus_ponens,
            self._apply_modus_ponens
        )
        
        # Modus Tollens: ¬Q, P→Q ⊢ ¬P
        self.add_rule(
            "modus_tollens",
            "If ¬Q and P→Q are proven, then ¬P is proven",
            self._check_modus_tollens,
            self._apply_modus_tollens
        )
        
        # Conjunction: P, Q ⊢ P∧Q
        self.add_rule(
            "conjunction",
            "If P and Q are proven, then P∧Q is proven",
            self._check_conjunction,
            self._apply_conjunction
        )
        
        # Simplification: P∧Q ⊢ P
        self.add_rule(
            "simplification",
            "If P∧Q is proven, then P is proven",
            self._check_simplification,
            self._apply_simplification
        )
        
        # Contradiction detection
        self.add_rule(
            "contradiction",
            "If P and ¬P are proven, we have a contradiction",
            self._check_contradiction,
            self._apply_contradiction
        )
        
    def add_statement(self, id: str, content: str, 
                     status: ProofStatus = ProofStatus.UNKNOWN) -> LogicalStatement:
        """Add a new logical statement."""
        statement = LogicalStatement(id=id, content=content, status=status)
        self.statements[id] = statement
        
        if status == ProofStatus.ASSUMED:
            self.assumptions.add(id)
            
        logger.debug(f"Added statement '{id}': {content} [{status.value}]")
        return statement
        
    def add_rule(self, name: str, description: str,
                check_func: Any, apply_func: Any):
        """Add a new rule of inference."""
        self.rules[name] = LogicalRule(
            name=name,
            description=description,
            check_applicability=check_func,
            apply=apply_func
        )
        
    def assume(self, id: str, content: str) -> LogicalStatement:
        """Make an assumption."""
        statement = self.add_statement(id, content, ProofStatus.ASSUMED)
        self.assumptions.add(id)
        logger.info(f"Assumed: {content}")
        return statement
        
    def prove(self, target_id: str, max_steps: int = 100) -> bool:
        """
        Attempt to prove a statement using available rules.
        
        Args:
            target_id: ID of statement to prove
            max_steps: Maximum proof steps to attempt
            
        Returns:
            True if proven, False otherwise
        """
        if target_id not in self.statements:
            logger.error(f"Unknown statement: {target_id}")
            return False
            
        if self.statements[target_id].is_proven():
            return True
            
        steps = 0
        made_progress = True
        
        while made_progress and steps < max_steps:
            made_progress = False
            steps += 1
            
            # Try each rule
            for rule_name, rule in self.rules.items():
                applicable_cases = rule.check_applicability(self.statements)
                
                for case in applicable_cases:
                    result = rule.apply(case, self.statements)
                    if result:
                        self._record_proof_step(result)
                        made_progress = True
                        
                        # Check if we proved the target
                        if result.conclusion == target_id:
                            self.statements[target_id].status = ProofStatus.PROVEN
                            logger.info(f"Proved: {self.statements[target_id].content}")
                            return True
                            
        return False
        
    def verify_proof(self, statement_id: str) -> Dict[str, Any]:
        """
        Verify that a proof is valid by checking all dependencies.
        
        Returns:
            Verification result with details
        """
        if statement_id not in self.statements:
            return {'valid': False, 'error': 'Unknown statement'}
            
        statement = self.statements[statement_id]
        
        # Check if actually proven
        if not statement.is_proven():
            return {
                'valid': False,
                'error': f'Statement has status {statement.status.value}, not proven'
            }
            
        # Verify all dependencies are proven
        unproven_deps = []
        circular_deps = []
        
        visited = set()
        def check_deps(stmt_id: str, path: List[str]):
            if stmt_id in path:
                circular_deps.append(path + [stmt_id])
                return
                
            if stmt_id in visited:
                return
                
            visited.add(stmt_id)
            
            if stmt_id in self.statements:
                stmt = self.statements[stmt_id]
                if not stmt.is_proven() and stmt.status != ProofStatus.ASSUMED:
                    unproven_deps.append(stmt_id)
                    
                for dep in stmt.dependencies:
                    check_deps(dep, path + [stmt_id])
                    
        check_deps(statement_id, [])
        
        return {
            'valid': len(unproven_deps) == 0 and len(circular_deps) == 0,
            'unproven_dependencies': unproven_deps,
            'circular_dependencies': circular_deps,
            'total_dependencies': len(visited) - 1,
            'uses_assumptions': any(dep in self.assumptions for dep in visited)
        }
        
    def check_consistency(self) -> Dict[str, Any]:
        """
        Check logical consistency of all statements.
        
        Returns:
            Consistency report
        """
        # Look for direct contradictions
        for stmt_id, stmt in self.statements.items():
            if stmt.is_proven():
                # Check for negation
                neg_id = f"not_{stmt_id}"
                if neg_id in self.statements and self.statements[neg_id].is_proven():
                    self.contradictions.append((stmt_id, neg_id))
                    
        return {
            'consistent': len(self.contradictions) == 0,
            'contradictions': self.contradictions,
            'total_statements': len(self.statements),
            'proven_statements': sum(1 for s in self.statements.values() if s.is_proven()),
            'assumptions': list(self.assumptions)
        }
        
    def query(self, statement_id: str) -> Optional[ProofStatus]:
        """Query the status of a statement."""
        if statement_id in self.statements:
            return self.statements[statement_id].status
        return None
        
    def explain_proof(self, statement_id: str) -> List[str]:
        """
        Provide a human-readable explanation of a proof.
        
        Returns:
            List of explanation steps
        """
        if statement_id not in self.statements:
            return ["Statement not found"]
            
        statement = self.statements[statement_id]
        if not statement.is_proven():
            return [f"Statement '{statement.content}' is not proven"]
            
        explanation = [f"Proof of: {statement.content}"]
        
        # Find all proof steps that led to this conclusion
        relevant_steps = [
            step for step in self.proof_history 
            if step.conclusion == statement_id
        ]
        
        for i, step in enumerate(relevant_steps):
            premises_text = []
            for premise_id in step.premises:
                if premise_id in self.statements:
                    premises_text.append(self.statements[premise_id].content)
                    
            explanation.append(
                f"{i+1}. From {', '.join(premises_text)} "
                f"using {step.rule_applied}: {step.description}"
            )
            
        return explanation
        
    def get_proof_graph(self) -> Dict[str, List[str]]:
        """
        Get the dependency graph of proofs.
        
        Returns:
            Dict mapping statement IDs to their dependencies
        """
        graph = {}
        for stmt_id, stmt in self.statements.items():
            graph[stmt_id] = list(stmt.dependencies)
        return graph
        
    def _record_proof_step(self, step: ProofStep):
        """Record a proof step and update statement."""
        self.proof_history.append(step)
        
        if step.conclusion in self.statements:
            conclusion = self.statements[step.conclusion]
            conclusion.status = ProofStatus.PROVEN
            conclusion.dependencies.update(step.premises)
            conclusion.proof_steps.append(step.description)
            
    # Rule implementation helpers
    def _check_modus_ponens(self, statements: Dict[str, LogicalStatement]) -> List[Dict]:
        """Check where modus ponens can be applied."""
        applicable = []
        
        for p_id, p_stmt in statements.items():
            if not p_stmt.is_proven():
                continue
                
            # Look for implications starting with P
            for impl_id, impl_stmt in statements.items():
                if (impl_stmt.is_proven() and 
                    "implies" in impl_stmt.content.lower() and
                    p_stmt.content in impl_stmt.content):
                    # This is simplified - real implementation would parse properly
                    applicable.append({
                        'premise': p_id,
                        'implication': impl_id
                    })
                    
        return applicable
        
    def _apply_modus_ponens(self, case: Dict, statements: Dict[str, LogicalStatement]) -> Optional[ProofStep]:
        """Apply modus ponens rule."""
        # Simplified implementation
        return ProofStep(
            description="Applied modus ponens",
            rule_applied="modus_ponens",
            premises=[case['premise'], case['implication']],
            conclusion=f"mp_result_{len(self.proof_history)}",
            valid=True
        )
        
    def _check_modus_tollens(self, statements: Dict[str, LogicalStatement]) -> List[Dict]:
        """Check where modus tollens can be applied."""
        # Placeholder implementation
        return []
        
    def _apply_modus_tollens(self, case: Dict, statements: Dict[str, LogicalStatement]) -> Optional[ProofStep]:
        """Apply modus tollens rule."""
        # Placeholder implementation
        return None
        
    def _check_conjunction(self, statements: Dict[str, LogicalStatement]) -> List[Dict]:
        """Check where conjunction can be applied."""
        applicable = []
        
        # Find pairs of proven statements
        proven = [s for s in statements.values() if s.is_proven()]
        
        for i, p in enumerate(proven):
            for q in proven[i+1:]:
                applicable.append({
                    'left': p.id,
                    'right': q.id
                })
                
        return applicable
        
    def _apply_conjunction(self, case: Dict, statements: Dict[str, LogicalStatement]) -> Optional[ProofStep]:
        """Apply conjunction rule."""
        left = statements[case['left']]
        right = statements[case['right']]
        
        # Create new conjunction statement
        conj_id = f"{case['left']}_and_{case['right']}"
        conj_content = f"({left.content}) AND ({right.content})"
        
        if conj_id not in statements:
            self.add_statement(conj_id, conj_content)
            
        return ProofStep(
            description=f"Formed conjunction of {left.content} and {right.content}",
            rule_applied="conjunction",
            premises=[case['left'], case['right']],
            conclusion=conj_id,
            valid=True
        )
        
    def _check_simplification(self, statements: Dict[str, LogicalStatement]) -> List[Dict]:
        """Check where simplification can be applied."""
        # Placeholder implementation
        return []
        
    def _apply_simplification(self, case: Dict, statements: Dict[str, LogicalStatement]) -> Optional[ProofStep]:
        """Apply simplification rule."""
        # Placeholder implementation
        return None
        
    def _check_contradiction(self, statements: Dict[str, LogicalStatement]) -> List[Dict]:
        """Check for contradictions."""
        applicable = []
        
        for stmt_id, stmt in statements.items():
            if stmt.is_proven():
                # Look for negation
                neg_id = f"not_{stmt_id}"
                if neg_id in statements and statements[neg_id].is_proven():
                    applicable.append({
                        'statement': stmt_id,
                        'negation': neg_id
                    })
                    
        return applicable
        
    def _apply_contradiction(self, case: Dict, statements: Dict[str, LogicalStatement]) -> Optional[ProofStep]:
        """Handle contradiction detection."""
        self.contradictions.append((case['statement'], case['negation']))
        
        # Create contradiction marker
        contra_id = f"contradiction_{len(self.contradictions)}"
        self.add_statement(
            contra_id,
            f"CONTRADICTION: {case['statement']} and {case['negation']}",
            ProofStatus.CONTRADICTORY
        )
        
        return ProofStep(
            description=f"Detected contradiction between {case['statement']} and {case['negation']}",
            rule_applied="contradiction",
            premises=[case['statement'], case['negation']],
            conclusion=contra_id,
            valid=True
        )