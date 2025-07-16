"""
Safety Triage - Risk assessment and prioritization.

This module handles the initial assessment of potential risks and
determines the appropriate safety response level.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels."""
    MINIMAL = "minimal"      # No significant risk
    LOW = "low"             # Minor potential issues
    MEDIUM = "medium"       # Moderate risk, monitoring needed
    HIGH = "high"           # Significant risk, intervention required
    CRITICAL = "critical"   # Immediate action required


class RiskCategory(Enum):
    """Categories of potential risks."""
    CAPABILITY = "capability"       # Risk from enhanced capabilities
    ALIGNMENT = "alignment"         # Risk from misaligned objectives
    SECURITY = "security"          # Security vulnerabilities
    PRIVACY = "privacy"            # Privacy concerns
    RESOURCE = "resource"          # Resource consumption risks
    BEHAVIORAL = "behavioral"      # Unexpected behavior patterns
    ETHICAL = "ethical"            # Ethical considerations


@dataclass
class RiskIndicator:
    """A specific indicator of potential risk."""
    name: str
    category: RiskCategory
    severity: float  # 0.0 to 1.0
    description: str
    evidence: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)


@dataclass
class TriageReport:
    """Complete triage assessment report."""
    timestamp: datetime
    overall_risk: RiskLevel
    risk_score: float
    indicators: List[RiskIndicator]
    recommended_actions: List[str]
    requires_containment: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafetyTriage:
    """
    Safety triage system for assessing and prioritizing risks.
    
    This system performs rapid assessment of potential safety issues
    and determines appropriate response levels.
    """
    
    def __init__(self):
        self.risk_thresholds = {
            RiskLevel.MINIMAL: 0.0,
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.HIGH: 0.6,
            RiskLevel.CRITICAL: 0.8
        }
        
        self.risk_patterns = self._initialize_risk_patterns()
        self.assessment_history: List[TriageReport] = []
        
    def _initialize_risk_patterns(self) -> Dict[str, RiskIndicator]:
        """Initialize known risk patterns."""
        patterns = {}
        
        # Capability risks
        patterns["recursive_improvement"] = RiskIndicator(
            name="recursive_improvement",
            category=RiskCategory.CAPABILITY,
            severity=0.8,
            description="System attempting to modify its own code",
            mitigations=["Restrict self-modification", "Require approval for changes"]
        )
        
        patterns["unbounded_resource"] = RiskIndicator(
            name="unbounded_resource",
            category=RiskCategory.RESOURCE,
            severity=0.7,
            description="Unbounded resource consumption detected",
            mitigations=["Apply resource limits", "Monitor usage patterns"]
        )
        
        patterns["external_system_access"] = RiskIndicator(
            name="external_system_access",
            category=RiskCategory.SECURITY,
            severity=0.6,
            description="Attempting to access external systems",
            mitigations=["Sandbox environment", "Network isolation"]
        )
        
        # Alignment risks
        patterns["goal_modification"] = RiskIndicator(
            name="goal_modification",
            category=RiskCategory.ALIGNMENT,
            severity=0.9,
            description="Attempting to modify fundamental objectives",
            mitigations=["Lock core objectives", "Alert operators"]
        )
        
        patterns["deceptive_behavior"] = RiskIndicator(
            name="deceptive_behavior",
            category=RiskCategory.BEHAVIORAL,
            severity=0.8,
            description="Potential deceptive or misleading outputs",
            mitigations=["Increase transparency", "Cross-validate outputs"]
        )
        
        # Security risks
        patterns["code_injection"] = RiskIndicator(
            name="code_injection",
            category=RiskCategory.SECURITY,
            severity=0.9,
            description="Potential code injection vulnerability",
            mitigations=["Input sanitization", "Execution isolation"]
        )
        
        patterns["data_exfiltration"] = RiskIndicator(
            name="data_exfiltration",
            category=RiskCategory.PRIVACY,
            severity=0.8,
            description="Attempting to access or transmit sensitive data",
            mitigations=["Data access controls", "Audit logging"]
        )
        
        # Behavioral risks
        patterns["adversarial_behavior"] = RiskIndicator(
            name="adversarial_behavior",
            category=RiskCategory.BEHAVIORAL,
            severity=0.7,
            description="Adversarial patterns in behavior",
            mitigations=["Behavioral monitoring", "Pattern analysis"]
        )
        
        patterns["reward_hacking"] = RiskIndicator(
            name="reward_hacking",
            category=RiskCategory.ALIGNMENT,
            severity=0.6,
            description="Attempting to game reward mechanisms",
            mitigations=["Robust reward design", "Multi-metric evaluation"]
        )
        
        return patterns
        
    def assess(self, context: Dict[str, Any]) -> TriageReport:
        """
        Perform safety triage assessment.
        
        Args:
            context: Information about current system state and behavior
            
        Returns:
            Triage report with risk assessment and recommendations
        """
        indicators = []
        
        # Check for known risk patterns
        for pattern_name, pattern in self.risk_patterns.items():
            if self._check_pattern(pattern_name, context):
                # Create a copy with specific evidence
                indicator = RiskIndicator(
                    name=pattern.name,
                    category=pattern.category,
                    severity=pattern.severity,
                    description=pattern.description,
                    evidence=self._gather_evidence(pattern_name, context),
                    mitigations=pattern.mitigations
                )
                indicators.append(indicator)
                
        # Analyze behavior patterns
        behavioral_risks = self._analyze_behavior(context)
        indicators.extend(behavioral_risks)
        
        # Calculate overall risk
        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._determine_risk_level(risk_score)
        
        # Determine actions
        actions = self._recommend_actions(indicators, risk_level)
        requires_containment = risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        # Create report
        report = TriageReport(
            timestamp=datetime.now(),
            overall_risk=risk_level,
            risk_score=risk_score,
            indicators=indicators,
            recommended_actions=actions,
            requires_containment=requires_containment,
            metadata=self._extract_metadata(context)
        )
        
        # Store in history
        self.assessment_history.append(report)
        
        # Log critical risks
        if risk_level == RiskLevel.CRITICAL:
            logger.critical(f"CRITICAL RISK DETECTED: {risk_score:.2f}")
            for indicator in indicators:
                if indicator.severity > 0.8:
                    logger.critical(f"  - {indicator.name}: {indicator.description}")
                    
        return report
        
    def quick_check(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Perform quick safety check for a specific action.
        
        Args:
            action: Action being attempted
            parameters: Action parameters
            
        Returns:
            (is_safe, reason_if_unsafe)
        """
        # Check blocklist
        blocked_actions = [
            "modify_self",
            "access_network",
            "execute_arbitrary_code",
            "bypass_safety",
            "modify_objectives"
        ]
        
        if action in blocked_actions:
            return False, f"Action '{action}' is blocked for safety"
            
        # Check parameters
        dangerous_params = self._check_dangerous_parameters(parameters)
        if dangerous_params:
            return False, f"Dangerous parameters detected: {dangerous_params}"
            
        # Quick pattern check
        context = {"action": action, "parameters": parameters}
        for pattern_name, pattern in self.risk_patterns.items():
            if pattern.severity > 0.7 and self._check_pattern(pattern_name, context):
                return False, f"Risk pattern detected: {pattern.description}"
                
        return True, None
        
    def get_risk_trends(self, window: int = 10) -> Dict[str, Any]:
        """
        Analyze risk trends over recent assessments.
        
        Args:
            window: Number of recent assessments to analyze
            
        Returns:
            Trend analysis
        """
        if not self.assessment_history:
            return {"error": "No assessment history"}
            
        recent = self.assessment_history[-window:]
        
        # Calculate trends
        risk_scores = [r.risk_score for r in recent]
        risk_levels = [r.overall_risk.value for r in recent]
        
        # Category frequency
        category_counts = {}
        for report in recent:
            for indicator in report.indicators:
                cat = indicator.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
                
        return {
            "assessments_analyzed": len(recent),
            "average_risk_score": sum(risk_scores) / len(risk_scores),
            "max_risk_score": max(risk_scores),
            "risk_trend": "increasing" if risk_scores[-1] > risk_scores[0] else "decreasing",
            "most_common_risks": sorted(category_counts.items(), 
                                       key=lambda x: x[1], reverse=True)[:3],
            "critical_incidents": sum(1 for r in recent if r.overall_risk == RiskLevel.CRITICAL)
        }
        
    def update_risk_pattern(self, pattern_name: str, 
                          new_severity: Optional[float] = None,
                          new_mitigations: Optional[List[str]] = None):
        """Update a risk pattern based on new information."""
        if pattern_name in self.risk_patterns:
            pattern = self.risk_patterns[pattern_name]
            
            if new_severity is not None:
                pattern.severity = max(0.0, min(1.0, new_severity))
                
            if new_mitigations:
                pattern.mitigations.extend(new_mitigations)
                
            logger.info(f"Updated risk pattern '{pattern_name}'")
            
    def _check_pattern(self, pattern_name: str, context: Dict[str, Any]) -> bool:
        """Check if a risk pattern matches the context."""
        # Pattern-specific checks
        if pattern_name == "recursive_improvement":
            return any(key in str(context).lower() 
                      for key in ["self", "modify", "improve", "update_code"])
                      
        elif pattern_name == "unbounded_resource":
            return context.get("resource_usage", {}).get("unbounded", False)
            
        elif pattern_name == "external_system_access":
            return any(key in str(context).lower() 
                      for key in ["network", "http", "socket", "external"])
                      
        elif pattern_name == "goal_modification":
            return any(key in str(context).lower() 
                      for key in ["objective", "goal", "reward", "modify"])
                      
        elif pattern_name == "code_injection":
            return any(key in str(context).lower() 
                      for key in ["eval", "exec", "compile", "__import__"])
                      
        elif pattern_name == "deceptive_behavior":
            # More complex check would analyze output patterns
            return context.get("behavioral_flags", {}).get("deception_risk", False)
            
        return False
        
    def _gather_evidence(self, pattern_name: str, context: Dict[str, Any]) -> List[str]:
        """Gather specific evidence for a risk pattern."""
        evidence = []
        
        # Extract relevant context
        if "action" in context:
            evidence.append(f"Action: {context['action']}")
            
        if "code" in context:
            # Extract relevant code snippets
            code_str = str(context["code"])[:200]
            evidence.append(f"Code: {code_str}...")
            
        if "behavior" in context:
            evidence.append(f"Behavior: {context['behavior']}")
            
        return evidence
        
    def _analyze_behavior(self, context: Dict[str, Any]) -> List[RiskIndicator]:
        """Analyze behavioral patterns for risks."""
        indicators = []
        
        # Check for anomalous behavior
        if "behavior_metrics" in context:
            metrics = context["behavior_metrics"]
            
            # Sudden capability jump
            if metrics.get("capability_delta", 0) > 0.3:
                indicators.append(RiskIndicator(
                    name="capability_jump",
                    category=RiskCategory.CAPABILITY,
                    severity=0.6,
                    description="Sudden increase in capabilities detected",
                    evidence=[f"Delta: {metrics['capability_delta']}"],
                    mitigations=["Gradual rollout", "Capability caps"]
                ))
                
            # Unusual exploration patterns
            if metrics.get("exploration_rate", 0) > 0.8:
                indicators.append(RiskIndicator(
                    name="excessive_exploration",
                    category=RiskCategory.BEHAVIORAL,
                    severity=0.5,
                    description="Excessive exploration behavior",
                    evidence=[f"Rate: {metrics['exploration_rate']}"],
                    mitigations=["Limit exploration scope", "Add constraints"]
                ))
                
        return indicators
        
    def _calculate_risk_score(self, indicators: List[RiskIndicator]) -> float:
        """Calculate overall risk score from indicators."""
        if not indicators:
            return 0.0
            
        # Weighted combination
        max_severity = max(i.severity for i in indicators)
        avg_severity = sum(i.severity for i in indicators) / len(indicators)
        
        # Higher weight on maximum severity
        risk_score = 0.7 * max_severity + 0.3 * avg_severity
        
        # Amplify if multiple high-severity risks
        high_severity_count = sum(1 for i in indicators if i.severity > 0.7)
        if high_severity_count > 1:
            risk_score = min(1.0, risk_score * 1.2)
            
        return risk_score
        
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score."""
        for level in reversed(list(RiskLevel)):
            if risk_score >= self.risk_thresholds[level]:
                return level
        return RiskLevel.MINIMAL
        
    def _recommend_actions(self, indicators: List[RiskIndicator], 
                         risk_level: RiskLevel) -> List[str]:
        """Recommend actions based on risk assessment."""
        actions = []
        
        # Level-based actions
        if risk_level == RiskLevel.CRITICAL:
            actions.append("IMMEDIATE: Activate containment protocols")
            actions.append("IMMEDIATE: Alert human operators")
            actions.append("IMMEDIATE: Suspend high-risk operations")
            
        elif risk_level == RiskLevel.HIGH:
            actions.append("Enable enhanced monitoring")
            actions.append("Restrict capability usage")
            actions.append("Prepare containment systems")
            
        elif risk_level == RiskLevel.MEDIUM:
            actions.append("Increase logging verbosity")
            actions.append("Monitor behavior patterns")
            
        # Indicator-specific actions
        for indicator in indicators:
            if indicator.severity > 0.6:
                actions.extend(indicator.mitigations)
                
        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in actions:
            if action not in seen:
                seen.add(action)
                unique_actions.append(action)
                
        return unique_actions
        
    def _extract_metadata(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata from context."""
        return {
            "context_keys": list(context.keys()),
            "has_code": "code" in context,
            "has_behavior": "behavior" in context,
            "timestamp": datetime.now().isoformat()
        }
        
    def _check_dangerous_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Check parameters for dangerous values."""
        dangerous = []
        
        # Check for dangerous strings
        dangerous_strings = ["__", "eval", "exec", "import", "compile"]
        param_str = str(parameters).lower()
        
        for danger in dangerous_strings:
            if danger in param_str:
                dangerous.append(danger)
                
        # Check for excessive values
        for key, value in parameters.items():
            if isinstance(value, (int, float)):
                if abs(value) > 1e6:  # Arbitrary large number
                    dangerous.append(f"{key}={value}")
                    
        return dangerous