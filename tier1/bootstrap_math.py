#!/usr/bin/env python3
"""
Mathematical reasoning bootstrap script for RegionAI.

This is the main entry point for running the mathematical reasoning engine.
It orchestrates the entire process of attempting proofs for theorems in the
curriculum and generates a comprehensive report of the results.
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .data.curriculum_factory import CurriculumFactory
from .data.math_curriculum import MathProblem
from .reasoning.planner import Planner
from .reasoning.proof_runner import ProofRunner
from .reasoning.tactic_executor import TacticExecutor, MockTacticExecutor
from .reasoning.lean_executor import LeanExecutor, LeanMockExecutor
from .reasoning.proof_trace import ProofTraceRecorder
from .reasoning.utility_updater import UtilityUpdater
from .reasoning.heuristics.math_foundations import reset_hypothesis_names
from .reasoning.concept_miner import ConceptMiner
from .language.lean_ast import ProofState, Theorem, Hypothesis
from .domain.exceptions import ExponentialSearchException, ProofTimeoutException
from .config import RegionAIConfig, DEFAULT_CONFIG
from .reporting.math_summary import generate_summary_report
from .knowledge.hub_v2 import KnowledgeHubV2
from .utils.dependency_factory import DependencyFactory


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProofAttemptResult:
    """Result of a single proof attempt."""
    theorem_name: str
    status: str  # SUCCESS, TIMEOUT, NO_PROGRESS, ERROR
    steps_taken: int = 0
    time_seconds: float = 0.0
    error_message: Optional[str] = None
    responsible_heuristic: Optional[str] = None
    proof_trace: Optional[List[Dict[str, Any]]] = None


@dataclass
class BootstrapSession:
    """Tracks the entire bootstrap session."""
    start_time: datetime = field(default_factory=datetime.now)
    results: List[ProofAttemptResult] = field(default_factory=list)
    config: RegionAIConfig = field(default_factory=lambda: DEFAULT_CONFIG)
    
    def add_result(self, result: ProofAttemptResult):
        """Add a proof attempt result."""
        self.results.append(result)
        
    def get_summary_stats(self) -> Dict[str, int]:
        """Get summary statistics."""
        stats = {
            'total': len(self.results),
            'success': 0,
            'timeout': 0,
            'no_progress': 0,
            'error': 0
        }
        
        for result in self.results:
            status_key = result.status.lower()
            if status_key in stats:
                stats[status_key] += 1
                
        return stats


class MathBootstrapper:
    """
    Orchestrates the mathematical reasoning bootstrap process.
    
    This class manages the entire workflow of loading theorems,
    attempting proofs, and collecting results.
    """
    
    def __init__(self, 
                 config: Optional[RegionAIConfig] = None,
                 use_mock_executor: bool = True,
                 curriculum_file: Optional[str] = None):
        """
        Initialize the bootstrapper.
        
        Args:
            config: Configuration to use (defaults to DEFAULT_CONFIG)
            use_mock_executor: Whether to use MockTacticExecutor (for testing)
            curriculum_file: Optional specific curriculum file to load
        """
        self.config = config or DEFAULT_CONFIG
        self.use_mock_executor = use_mock_executor
        self.curriculum_file = curriculum_file
        self.session = BootstrapSession(config=self.config)
        
        # Create dependency factory
        self.factory = DependencyFactory(config=self.config)
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize all required components."""
        logger.info("Initializing bootstrap components...")
        
        # Create curriculum factory and load math curriculum
        self.curriculum_factory = CurriculumFactory()
        
        # For math curriculum, we need to load it directly
        from .data.math_curriculum import MathCurriculum
        self.math_curriculum = MathCurriculum(curriculum_file=self.curriculum_file)
        self.math_curriculum.load_curriculum()
        self.curriculum = self.math_curriculum
        
        # Create tactic executor
        if self.use_mock_executor:
            logger.info("Using MockTacticExecutor (no Lean required)")
            self.tactic_executor = MockTacticExecutor()
        else:
            logger.info("Using real Lean 4 executor")
            try:
                self.tactic_executor = LeanExecutor()
            except Exception as e:
                logger.warning(f"Failed to initialize LeanExecutor: {e}")
                logger.info("Falling back to MockTacticExecutor")
                self.tactic_executor = MockTacticExecutor()
                self.use_mock_executor = True
        
        # Create utility updater
        self.utility_updater = UtilityUpdater()
        
        # Initialize KnowledgeHub for concept mining using factory
        self.hub = self.factory.create_knowledge_hub()
        
        # Create planner
        self.planner = Planner(
            config=self.config,
            utility_updater=self.utility_updater,
            hub=self.hub
        )
        
        # Create traces directory
        self.traces_dir = Path("traces")
        self.traces_dir.mkdir(exist_ok=True)
        
        logger.info("Bootstrap components initialized")
        
    def run(self) -> BootstrapSession:
        """
        Run the bootstrap process on all theorems in the curriculum.
        
        Returns:
            The completed BootstrapSession with all results
        """
        logger.info("Starting mathematical reasoning bootstrap...")
        logger.info(f"Curriculum loaded with {len(self.curriculum.problems)} theorems")
        
        # Sort problems by difficulty for a natural progression
        sorted_problems = sorted(self.curriculum.problems, key=lambda p: p.difficulty)
        
        for i, problem in enumerate(sorted_problems, 1):
            if not isinstance(problem, MathProblem):
                logger.warning(f"Skipping non-math problem: {problem}")
                continue
                
            theorem = problem.theorem
            print(f"\n{'='*60}")
            print(f"--- Attempting proof {i}/{len(sorted_problems)}: {theorem.name} ---")
            print(f"Statement: {theorem.statement}")
            print(f"Difficulty: {problem.difficulty:.2f}")
            print(f"{'='*60}")
            
            # Reset hypothesis name generator for each proof
            reset_hypothesis_names()
            
            # Attempt the proof
            result = self._attempt_proof(theorem)
            self.session.add_result(result)
            
            # Display result
            self._display_result(result)
            
        logger.info("Bootstrap process completed")
        return self.session
    
    def _attempt_proof(self, theorem: Theorem) -> ProofAttemptResult:
        """
        Attempt to prove a single theorem.
        
        Args:
            theorem: The theorem to prove
            
        Returns:
            ProofAttemptResult with the outcome
        """
        start_time = time.time()
        
        # Create initial proof state
        proof_state = ProofState(
            theorem_name=theorem.name,
            hypotheses=theorem.hypotheses,
            current_goal=theorem.statement,
            remaining_goals=[],
            is_complete=False
        )
        
        # Create trace recorder for this proof attempt
        trace_file = self.traces_dir / f"{theorem.name}_{int(time.time())}.jsonl"
        
        # Use context manager to ensure proper cleanup
        with ProofTraceRecorder(trace_file) as trace_recorder:
            trace_recorder.set_theorem_info(theorem.name, theorem.statement)
            
            # Create proof runner with safety guards
            proof_runner = ProofRunner(
                config=self.config,
                theorem=theorem,
                tactic_executor=self.tactic_executor,
                trace_recorder=trace_recorder
            )
            
            try:
                # Use planner to attempt proof
                with proof_runner:
                    success = self.planner.attempt_proof(
                        proof_state=proof_state,
                        proof_runner=proof_runner,
                        max_steps=100
                    )
                
            elapsed_time = time.time() - start_time
            
            if success:
                trace_recorder.record_custom_event('proof_complete', {
                    'success': True,
                    'steps': proof_runner.metrics.steps_taken
                })
                
                return ProofAttemptResult(
                    theorem_name=theorem.name,
                    status="SUCCESS",
                    steps_taken=proof_runner.metrics.steps_taken,
                    time_seconds=elapsed_time
                )
            else:
                # Proof incomplete but no exception
                trace_recorder.record_custom_event('proof_complete', {
                    'success': False,
                    'reason': 'incomplete',
                    'steps': proof_runner.metrics.steps_taken
                })
                
                return ProofAttemptResult(
                    theorem_name=theorem.name,
                    status="NO_PROGRESS",
                    steps_taken=proof_runner.metrics.steps_taken,
                    time_seconds=elapsed_time,
                    error_message="Proof incomplete after maximum steps"
                )
                    
            except ProofTimeoutException as e:
                elapsed_time = time.time() - start_time
                trace_recorder.record_custom_event('proof_complete', {
                'success': False,
                'reason': 'timeout',
                'steps': proof_runner.metrics.steps_taken
            })
                
                return ProofAttemptResult(
                    theorem_name=theorem.name,
                    status="TIMEOUT",
                    steps_taken=proof_runner.metrics.steps_taken,
                    time_seconds=elapsed_time,
                    error_message=str(e),
                    responsible_heuristic=proof_runner.current_heuristic
                )
            
            except ExponentialSearchException as e:
                elapsed_time = time.time() - start_time
                trace_recorder.record_custom_event('proof_complete', {
                'success': False,
                'reason': 'exponential_search',
                'steps': proof_runner.metrics.steps_taken
            })
            
                return ProofAttemptResult(
                    theorem_name=theorem.name,
                    status="NO_PROGRESS",
                    steps_taken=e.steps_taken,
                    time_seconds=elapsed_time,
                    error_message=str(e),
                    responsible_heuristic=e.context.get('current_heuristic')
                )
            
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Unexpected error during proof attempt: {e}", exc_info=True)
                
                # trace_recorder is guaranteed to exist in this context
                trace_recorder.record_custom_event('proof_complete', {
                    'success': False,
                    'reason': 'error',
                    'error': str(e),
                    'steps': proof_runner.metrics.steps_taken if 'proof_runner' in locals() else 0
                })
                
                return ProofAttemptResult(
                    theorem_name=theorem.name,
                    status="ERROR",
                    steps_taken=proof_runner.metrics.steps_taken if 'proof_runner' in locals() else 0,
                    time_seconds=elapsed_time,
                    error_message=f"Unexpected error: {str(e)}"
                )
    
    def _display_result(self, result: ProofAttemptResult):
        """Display the result of a proof attempt."""
        status_emoji = {
            "SUCCESS": "✅",
            "TIMEOUT": "⏱️",
            "NO_PROGRESS": "🔄",
            "ERROR": "❌"
        }.get(result.status, "❓")
        
        print(f"\n{status_emoji} Result: {result.status}")
        print(f"   Steps: {result.steps_taken}")
        print(f"   Time: {result.time_seconds:.2f}s")
        
        if result.error_message:
            print(f"   Error: {result.error_message}")
            
        if result.responsible_heuristic:
            print(f"   Responsible heuristic: {result.responsible_heuristic}")


def main():
    """Main entry point for the bootstrap script."""
    print("RegionAI Mathematical Reasoning Bootstrap")
    print("========================================\n")
    
    # Parse command line arguments if needed
    import argparse
    parser = argparse.ArgumentParser(description="Bootstrap RegionAI's mathematical reasoning")
    parser.add_argument(
        '--use-lean',
        action='store_true',
        help='Use real Lean executor instead of mock (requires Lean installation)'
    )
    parser.add_argument(
        '--max-time',
        type=int,
        default=600,
        help='Maximum time per proof in seconds (default: 600)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for detailed results (optional)'
    )
    parser.add_argument(
        '--self-improve',
        action='store_true',
        help='Run self-improvement cycle (two passes with learning)'
    )
    parser.add_argument(
        '--curriculum-file',
        type=str,
        help='Specific curriculum file to load (e.g., test_self_improve.lean)'
    )
    
    args = parser.parse_args()
    
    # Create config with custom timeout if specified
    config = RegionAIConfig(max_proof_sec=args.max_time)
    
    if args.self_improve:
        # Run the self-improvement cycle
        return run_self_improvement_cycle(config, not args.use_lean, args.output, args.curriculum_file)
    else:
        # Run standard single pass
        return run_standard_bootstrap(config, not args.use_lean, args.output, args.curriculum_file)


def run_standard_bootstrap(config, use_mock_executor, output_file, curriculum_file=None):
    """Run a standard single-pass bootstrap."""
    # Create and run bootstrapper
    bootstrapper = MathBootstrapper(
        config=config,
        use_mock_executor=use_mock_executor,
        curriculum_file=curriculum_file
    )
    
    # Run the bootstrap process
    session = bootstrapper.run()
    
    # Generate and display summary report
    print("\n" + "="*60)
    print("BOOTSTRAP SUMMARY REPORT")
    print("="*60)
    
    report = generate_summary_report(session)
    print(report)
    
    # Save detailed results if requested
    if output_file:
        output_path = Path(output_file)
        output_path.write_text(report)
        print(f"\nDetailed report saved to: {output_path}")
    
    # Run the Concept Miner to extract new concepts from successful proofs
    print("\n" + "="*60)
    print("CONCEPT MINING")
    print("="*60)
    
    concept_miner = ConceptMiner(
        hub=bootstrapper.hub,
        traces_dir=bootstrapper.traces_dir
    )
    
    new_concepts = concept_miner.mine_from_traces()
    miner_report = concept_miner.generate_report(new_concepts)
    print(miner_report)
    
    # Exit with appropriate code
    stats = session.get_summary_stats()
    if stats['success'] == 0:
        print("\n⚠️  No theorems were successfully proved.")
        return 1
    elif stats['error'] > 0:
        print(f"\n⚠️  {stats['error']} theorems encountered errors.")
        return 1
    else:
        print(f"\n✅ Successfully proved {stats['success']}/{stats['total']} theorems!")
        return 0


def run_self_improvement_cycle(config, use_mock_executor, output_file, curriculum_file=None):
    """Run the self-improvement cycle with two passes."""
    print("="*60)
    print("SELF-IMPROVEMENT CYCLE - RUN 1 (Discovery)")
    print("="*60)
    
    # First run: Discovery
    bootstrapper1 = MathBootstrapper(
        config=config,
        use_mock_executor=use_mock_executor,
        curriculum_file=curriculum_file
    )
    
    session1 = bootstrapper1.run()
    stats1 = session1.get_summary_stats()
    
    # Track which theorems failed
    failed_theorems = []
    for result in session1.results:
        if result.status != "SUCCESS":
            # Find the corresponding theorem
            for problem in bootstrapper1.curriculum.problems:
                if hasattr(problem, 'theorem') and problem.theorem.name == result.theorem_name:
                    failed_theorems.append(problem.theorem)
                    break
    
    print(f"\nRun 1 Results: {stats1['success']}/{stats1['total']} theorems proved")
    print(f"Failed theorems: {len(failed_theorems)}")
    
    if stats1['success'] == 0:
        print("\n⚠️  No theorems were proved in Run 1. Cannot demonstrate improvement.")
        return 1
    
    # Mine concepts from successful proofs
    print("\n" + "="*60)
    print("MINING CONCEPTS FROM RUN 1")
    print("="*60)
    
    concept_miner = ConceptMiner(
        hub=bootstrapper1.hub,
        traces_dir=bootstrapper1.traces_dir
    )
    
    new_concepts = concept_miner.mine_from_traces()
    print(f"Mined {len(new_concepts)} new proof patterns")
    
    if len(new_concepts) == 0:
        print("\n⚠️  No patterns were mined. Cannot demonstrate improvement.")
        return 1
    
    # Clear traces for second run
    import shutil
    if bootstrapper1.traces_dir.exists():
        shutil.rmtree(bootstrapper1.traces_dir)
    bootstrapper1.traces_dir.mkdir(exist_ok=True)
    
    # Second run: Improvement (only on failed theorems)
    print("\n" + "="*60)
    print("SELF-IMPROVEMENT CYCLE - RUN 2 (Improvement)")
    print("="*60)
    print(f"Attempting {len(failed_theorems)} previously failed theorems with learned patterns...")
    
    # Create a new bootstrapper that shares the enriched knowledge hub
    bootstrapper2 = MathBootstrapper(
        config=config,
        use_mock_executor=use_mock_executor,
        curriculum_file=curriculum_file
    )
    # Share the enriched hub
    bootstrapper2.hub = bootstrapper1.hub
    bootstrapper2.planner.hub = bootstrapper1.hub
    
    # Run only on failed theorems
    improvement_session = BootstrapSession(config=config)
    
    for i, theorem in enumerate(failed_theorems, 1):
        print(f"\n[{i}/{len(failed_theorems)}] Attempting {theorem.name}: {theorem.statement}")
        result = bootstrapper2._attempt_proof(theorem)
        improvement_session.add_result(result)
        bootstrapper2._display_result(result)
    
    # Generate improvement report
    print("\n" + "="*60)
    print("SELF-IMPROVEMENT REPORT")
    print("="*60)
    
    stats2 = improvement_session.get_summary_stats()
    improved_theorems = []
    
    for result in improvement_session.results:
        if result.status == "SUCCESS":
            improved_theorems.append(result.theorem_name)
    
    print(f"\nRun 1: {stats1['success']}/{stats1['total']} theorems proved")
    print(f"Run 2: {stats2['success']}/{len(failed_theorems)} previously failed theorems now proved")
    
    if improved_theorems:
        print(f"\n🎉 IMPROVEMENT DEMONSTRATED! The following theorems were solved using learned patterns:")
        for name in improved_theorems:
            print(f"  - {name}")
        
        # Try to identify which patterns helped
        print("\nLearned patterns that may have contributed:")
        for concept in new_concepts[:3]:  # Show top 3
            print(f"  - {concept.name}: {concept.description}")
            print(f"    Pattern: {concept.metadata.get('pattern', 'N/A')}")
    else:
        print("\n⚠️  No improvement demonstrated in Run 2.")
    
    # Save detailed report if requested
    if output_file:
        full_report = f"""Self-Improvement Cycle Report
=============================

Run 1 (Discovery):
{generate_summary_report(session1)}

Mined Concepts:
{concept_miner.generate_report(new_concepts)}

Run 2 (Improvement on {len(failed_theorems)} failed theorems):
{generate_summary_report(improvement_session)}

Improved Theorems: {', '.join(improved_theorems) if improved_theorems else 'None'}
"""
        Path(output_file).write_text(full_report)
        print(f"\nDetailed report saved to: {output_file}")
    
    return 0 if improved_theorems else 1


if __name__ == "__main__":
    exit(main())