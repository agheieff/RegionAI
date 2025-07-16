"""
Observer Brain - Meta-cognitive Monitor

This brain module observes and monitors the other cognitive processes,
detecting anomalies, managing disagreements, and ensuring system health.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Severity levels for metacognitive alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CognitiveState(Enum):
    """Overall cognitive system state."""
    HEALTHY = "healthy"
    STRESSED = "stressed"
    OVERLOADED = "overloaded"
    CONFUSED = "confused"
    RECOVERING = "recovering"


@dataclass
class Observation:
    """A single metacognitive observation."""
    timestamp: float
    brain: str  # Which brain was observed
    metric: str  # What was measured
    value: Any
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Disagreement:
    """Represents disagreement between cognitive modules."""
    timestamp: float
    brain1: str
    brain2: str
    topic: str
    details: Dict[str, Any]
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class Alert:
    """A metacognitive alert."""
    timestamp: float
    level: AlertLevel
    source: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


class ObserverBrain:
    """
    The Observer brain monitors metacognitive processes.
    
    Core responsibilities:
    - Monitor performance of other cognitive modules
    - Detect anomalies and inconsistencies
    - Manage inter-module disagreements
    - Track system health and resource usage
    - Trigger interventions when needed
    """
    
    def __init__(self, observation_window: int = 100):
        self.observation_window = observation_window
        self.observations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=observation_window))
        self.disagreements: List[Disagreement] = []
        self.alerts: List[Alert] = []
        self.brain_states: Dict[str, CognitiveState] = {}
        self.performance_baselines: Dict[str, Dict[str, float]] = {}
        self.intervention_history: List[Dict] = []
        
        # Thresholds for anomaly detection
        self.thresholds = {
            'response_time': {'warning': 5.0, 'error': 10.0},
            'confidence': {'warning': 0.3, 'error': 0.1},
            'error_rate': {'warning': 0.2, 'error': 0.5},
            'disagreement_rate': {'warning': 0.3, 'error': 0.6}
        }
        
    def observe(self, brain: str, metric: str, value: Any, context: Dict[str, Any] = None):
        """
        Record an observation about a cognitive module.
        
        Args:
            brain: Name of the brain being observed
            metric: What metric is being measured
            value: The measured value
            context: Additional context
        """
        obs = Observation(
            timestamp=time.time(),
            brain=brain,
            metric=metric,
            value=value,
            context=context or {}
        )
        
        self.observations[f"{brain}_{metric}"].append(obs)
        
        # Check for anomalies
        self._check_anomalies(brain, metric, value)
        
        # Update brain state
        self._update_brain_state(brain)
        
    def detect_disagreement(self, brain1: str, opinion1: Any,
                          brain2: str, opinion2: Any,
                          topic: str) -> Optional[Disagreement]:
        """
        Detect and record disagreement between cognitive modules.
        
        Args:
            brain1: First brain
            opinion1: First brain's opinion/output
            brain2: Second brain
            opinion2: Second brain's opinion/output
            topic: What they disagree about
            
        Returns:
            Disagreement object if significant disagreement detected
        """
        # Simple disagreement detection - can be made more sophisticated
        if opinion1 != opinion2:
            disagreement = Disagreement(
                timestamp=time.time(),
                brain1=brain1,
                brain2=brain2,
                topic=topic,
                details={
                    'opinion1': str(opinion1)[:100],
                    'opinion2': str(opinion2)[:100]
                }
            )
            
            self.disagreements.append(disagreement)
            
            # Alert if disagreement rate is high
            recent_disagreements = sum(
                1 for d in self.disagreements[-10:]
                if d.brain1 in [brain1, brain2] or d.brain2 in [brain1, brain2]
            )
            
            if recent_disagreements > 5:
                self.raise_alert(
                    AlertLevel.WARNING,
                    "observer",
                    f"High disagreement rate between {brain1} and {brain2}",
                    {'count': recent_disagreements}
                )
                
            return disagreement
            
        return None
        
    def assess_confidence(self, brain: str, decision: Any) -> float:
        """
        Assess confidence in a brain's decision based on historical performance.
        
        Args:
            brain: Which brain made the decision
            decision: The decision made
            
        Returns:
            Confidence score [0, 1]
        """
        # Base confidence on recent performance
        base_confidence = 0.7
        
        # Check recent error rate
        error_obs = self.observations.get(f"{brain}_error_rate", [])
        if error_obs:
            recent_errors = [o.value for o in error_obs[-10:]]
            avg_error = sum(recent_errors) / len(recent_errors)
            base_confidence *= (1 - avg_error)
            
        # Check brain state
        brain_state = self.brain_states.get(brain, CognitiveState.HEALTHY)
        state_multipliers = {
            CognitiveState.HEALTHY: 1.0,
            CognitiveState.STRESSED: 0.8,
            CognitiveState.OVERLOADED: 0.5,
            CognitiveState.CONFUSED: 0.3,
            CognitiveState.RECOVERING: 0.7
        }
        base_confidence *= state_multipliers[brain_state]
        
        # Check for recent disagreements
        recent_disagreements = sum(
            1 for d in self.disagreements[-20:]
            if not d.resolved and (d.brain1 == brain or d.brain2 == brain)
        )
        if recent_disagreements > 3:
            base_confidence *= 0.8
            
        return min(1.0, max(0.0, base_confidence))
        
    def should_intervene(self) -> Tuple[bool, Optional[str]]:
        """
        Determine if metacognitive intervention is needed.
        
        Returns:
            (should_intervene, reason)
        """
        # Check for critical alerts
        recent_critical = [
            a for a in self.alerts[-10:]
            if a.level == AlertLevel.CRITICAL
        ]
        if recent_critical:
            return True, f"Critical alert: {recent_critical[-1].message}"
            
        # Check overall system state
        unhealthy_brains = [
            brain for brain, state in self.brain_states.items()
            if state in [CognitiveState.OVERLOADED, CognitiveState.CONFUSED]
        ]
        if len(unhealthy_brains) >= 2:
            return True, f"Multiple brains unhealthy: {unhealthy_brains}"
            
        # Check disagreement rate
        unresolved = sum(1 for d in self.disagreements[-20:] if not d.resolved)
        if unresolved > 10:
            return True, f"High unresolved disagreement rate: {unresolved}"
            
        return False, None
        
    def intervene(self, reason: str) -> Dict[str, Any]:
        """
        Perform metacognitive intervention.
        
        Args:
            reason: Why intervention is needed
            
        Returns:
            Intervention plan
        """
        intervention = {
            'timestamp': time.time(),
            'reason': reason,
            'actions': [],
            'expected_outcomes': []
        }
        
        # Analyze the reason and determine actions
        if "overloaded" in reason.lower():
            intervention['actions'].extend([
                "Reduce thinking depth to FAST mode",
                "Defer non-critical tasks",
                "Increase time limits"
            ])
            intervention['expected_outcomes'].append("Reduced cognitive load")
            
        elif "disagreement" in reason.lower():
            intervention['actions'].extend([
                "Initiate consensus protocol",
                "Request additional evidence",
                "Consult logic brain for consistency check"
            ])
            intervention['expected_outcomes'].append("Resolved disagreements")
            
        elif "critical alert" in reason.lower():
            intervention['actions'].extend([
                "Pause all operations",
                "Run diagnostic checks",
                "Reset affected modules"
            ])
            intervention['expected_outcomes'].append("System stability restored")
            
        self.intervention_history.append(intervention)
        
        # Trigger recovery mode
        for brain in self.brain_states:
            if self.brain_states[brain] in [CognitiveState.OVERLOADED, CognitiveState.CONFUSED]:
                self.brain_states[brain] = CognitiveState.RECOVERING
                
        return intervention
        
    def resolve_disagreement(self, disagreement_index: int, resolution: str):
        """Mark a disagreement as resolved."""
        if 0 <= disagreement_index < len(self.disagreements):
            self.disagreements[disagreement_index].resolved = True
            self.disagreements[disagreement_index].resolution = resolution
            
    def raise_alert(self, level: AlertLevel, source: str, message: str, data: Dict[str, Any] = None):
        """Raise a metacognitive alert."""
        alert = Alert(
            timestamp=time.time(),
            level=level,
            source=source,
            message=message,
            data=data or {}
        )
        self.alerts.append(alert)
        
        logger.log(
            logging.INFO if level == AlertLevel.INFO else
            logging.WARNING if level == AlertLevel.WARNING else
            logging.ERROR,
            f"[{level.value}] {source}: {message}"
        )
        
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health report."""
        total_brains = len(self.brain_states)
        healthy_brains = sum(1 for state in self.brain_states.values() 
                           if state == CognitiveState.HEALTHY)
        
        recent_alerts = defaultdict(int)
        for alert in self.alerts[-50:]:
            recent_alerts[alert.level.value] += 1
            
        return {
            'overall_state': self._compute_overall_state(),
            'brain_states': dict(self.brain_states),
            'health_percentage': (healthy_brains / total_brains * 100) if total_brains > 0 else 0,
            'recent_alerts': dict(recent_alerts),
            'unresolved_disagreements': sum(1 for d in self.disagreements if not d.resolved),
            'recent_interventions': len(self.intervention_history[-10:]),
            'performance_summary': self._get_performance_summary()
        }
        
    def _check_anomalies(self, brain: str, metric: str, value: Any):
        """Check if a metric value is anomalous."""
        # Get baseline if exists
        if brain in self.performance_baselines and metric in self.performance_baselines[brain]:
            baseline = self.performance_baselines[brain][metric]
            
            # Simple anomaly detection - can be made more sophisticated
            if isinstance(value, (int, float)):
                deviation = abs(value - baseline) / baseline if baseline != 0 else float('inf')
                
                if deviation > 2.0:  # More than 200% deviation
                    self.raise_alert(
                        AlertLevel.WARNING,
                        "observer",
                        f"Anomalous {metric} for {brain}: {value} (baseline: {baseline})",
                        {'brain': brain, 'metric': metric, 'value': value, 'baseline': baseline}
                    )
                    
        # Check against thresholds
        if metric in self.thresholds and isinstance(value, (int, float)):
            thresholds = self.thresholds[metric]
            if 'error' in thresholds and value > thresholds['error']:
                self.raise_alert(
                    AlertLevel.ERROR,
                    "observer",
                    f"{metric} exceeds error threshold for {brain}: {value}",
                    {'brain': brain, 'metric': metric, 'value': value}
                )
            elif 'warning' in thresholds and value > thresholds['warning']:
                self.raise_alert(
                    AlertLevel.WARNING,
                    "observer",
                    f"{metric} exceeds warning threshold for {brain}: {value}",
                    {'brain': brain, 'metric': metric, 'value': value}
                )
                
    def _update_brain_state(self, brain: str):
        """Update cognitive state of a brain based on observations."""
        # Get recent observations
        error_rate = self._get_recent_average(f"{brain}_error_rate")
        response_time = self._get_recent_average(f"{brain}_response_time")
        
        # Determine state
        if error_rate is not None and error_rate > 0.5:
            self.brain_states[brain] = CognitiveState.CONFUSED
        elif response_time is not None and response_time > 10.0:
            self.brain_states[brain] = CognitiveState.OVERLOADED
        elif error_rate is not None and error_rate > 0.2:
            self.brain_states[brain] = CognitiveState.STRESSED
        elif brain in self.brain_states and self.brain_states[brain] == CognitiveState.RECOVERING:
            # Check if recovered
            if (error_rate is None or error_rate < 0.1) and (response_time is None or response_time < 2.0):
                self.brain_states[brain] = CognitiveState.HEALTHY
        else:
            self.brain_states[brain] = CognitiveState.HEALTHY
            
    def _get_recent_average(self, metric_key: str) -> Optional[float]:
        """Get average of recent observations for a metric."""
        if metric_key in self.observations and self.observations[metric_key]:
            recent = [o.value for o in self.observations[metric_key][-10:]
                     if isinstance(o.value, (int, float))]
            if recent:
                return sum(recent) / len(recent)
        return None
        
    def _compute_overall_state(self) -> str:
        """Compute overall system state."""
        if not self.brain_states:
            return "unknown"
            
        state_counts = defaultdict(int)
        for state in self.brain_states.values():
            state_counts[state] += 1
            
        # If any brain is confused or multiple are overloaded
        if state_counts[CognitiveState.CONFUSED] > 0:
            return "confused"
        elif state_counts[CognitiveState.OVERLOADED] >= 2:
            return "overloaded"
        elif state_counts[CognitiveState.STRESSED] >= 2:
            return "stressed"
        elif state_counts[CognitiveState.RECOVERING] > 0:
            return "recovering"
        else:
            return "healthy"
            
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all brains."""
        summary = {}
        
        for brain in set(obs.split('_')[0] for obs in self.observations.keys()):
            brain_summary = {}
            
            # Get key metrics
            for metric in ['error_rate', 'response_time', 'confidence']:
                avg = self._get_recent_average(f"{brain}_{metric}")
                if avg is not None:
                    brain_summary[metric] = round(avg, 3)
                    
            if brain_summary:
                summary[brain] = brain_summary
                
        return summary