"""
Sensorimotor Brain - Embodied Interaction

This brain module handles sensory perception, motor control, and
the coordination between perception and action in the environment.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


class SensorType(Enum):
    """Types of sensory inputs."""
    VISUAL = "visual"
    TEXTUAL = "textual"
    NUMERIC = "numeric"
    STRUCTURED = "structured"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"


class ActionType(Enum):
    """Types of motor actions."""
    READ = "read"
    WRITE = "write"
    TRANSFORM = "transform"
    NAVIGATE = "navigate"
    QUERY = "query"
    EXECUTE = "execute"


@dataclass
class SensoryInput:
    """Represents a sensory perception."""
    sensor_type: SensorType
    data: Any
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False


@dataclass
class MotorAction:
    """Represents a motor action to perform."""
    action_type: ActionType
    parameters: Dict[str, Any]
    expected_outcome: Optional[Any] = None
    constraints: List[str] = field(default_factory=list)
    
    
@dataclass
class SensorimotorLoop:
    """A perception-action loop."""
    perception: SensoryInput
    processing: Dict[str, Any]
    action: MotorAction
    outcome: Optional[Any] = None
    success: bool = False


@dataclass
class AffordancePattern:
    """Learned pattern of what actions are possible given perceptions."""
    name: str
    perception_features: Dict[str, Any]
    possible_actions: List[ActionType]
    success_rate: float
    usage_count: int = 0


class SensorimotorBrain:
    """
    The Sensorimotor brain handles embodied interaction with the environment.
    
    Core responsibilities:
    - Process sensory inputs
    - Plan and execute motor actions
    - Learn sensorimotor patterns
    - Coordinate perception-action loops
    - Discover affordances in the environment
    """
    
    def __init__(self, buffer_size: int = 100):
        self.buffer_size = buffer_size
        self.sensory_buffer: deque = deque(maxlen=buffer_size)
        self.action_history: deque = deque(maxlen=buffer_size)
        self.active_loops: List[SensorimotorLoop] = []
        self.affordances: Dict[str, AffordancePattern] = {}
        
        # Sensory processors
        self.sensory_processors: Dict[SensorType, Callable] = {}
        self._register_default_processors()
        
        # Motor controllers
        self.motor_controllers: Dict[ActionType, Callable] = {}
        self._register_default_controllers()
        
        # Feature extractors for different sensor types
        self.feature_extractors: Dict[SensorType, Callable] = {}
        self._register_default_extractors()
        
    def _register_default_processors(self):
        """Register default sensory processors."""
        self.sensory_processors[SensorType.TEXTUAL] = self._process_textual
        self.sensory_processors[SensorType.VISUAL] = self._process_visual
        self.sensory_processors[SensorType.NUMERIC] = self._process_numeric
        self.sensory_processors[SensorType.STRUCTURED] = self._process_structured
        
    def _register_default_controllers(self):
        """Register default motor controllers."""
        self.motor_controllers[ActionType.READ] = self._control_read
        self.motor_controllers[ActionType.WRITE] = self._control_write
        self.motor_controllers[ActionType.TRANSFORM] = self._control_transform
        self.motor_controllers[ActionType.QUERY] = self._control_query
        
    def _register_default_extractors(self):
        """Register default feature extractors."""
        self.feature_extractors[SensorType.TEXTUAL] = self._extract_text_features
        self.feature_extractors[SensorType.VISUAL] = self._extract_visual_features
        self.feature_extractors[SensorType.NUMERIC] = self._extract_numeric_features
        
    def perceive(self, sensor_type: SensorType, data: Any,
                metadata: Dict[str, Any] = None) -> SensoryInput:
        """
        Process a sensory input.
        
        Args:
            sensor_type: Type of sensor
            data: Raw sensory data
            metadata: Additional metadata
            
        Returns:
            Processed sensory input
        """
        import time
        
        sensory_input = SensoryInput(
            sensor_type=sensor_type,
            data=data,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        # Process if processor available
        if sensor_type in self.sensory_processors:
            processed_data = self.sensory_processors[sensor_type](data)
            sensory_input.metadata['processed'] = processed_data
            sensory_input.processed = True
            
        self.sensory_buffer.append(sensory_input)
        
        # Check for affordances
        self._update_affordances(sensory_input)
        
        logger.debug(f"Perceived {sensor_type.value} input")
        return sensory_input
        
    def act(self, action_type: ActionType, parameters: Dict[str, Any],
           expected_outcome: Any = None) -> Tuple[bool, Any]:
        """
        Execute a motor action.
        
        Args:
            action_type: Type of action
            parameters: Action parameters
            expected_outcome: What we expect to happen
            
        Returns:
            (success, actual_outcome)
        """
        action = MotorAction(
            action_type=action_type,
            parameters=parameters,
            expected_outcome=expected_outcome
        )
        
        # Execute if controller available
        if action_type in self.motor_controllers:
            try:
                outcome = self.motor_controllers[action_type](parameters)
                success = True
                
                # Check if outcome matches expectation
                if expected_outcome is not None:
                    success = self._matches_expectation(outcome, expected_outcome)
                    
            except Exception as e:
                logger.error(f"Action {action_type.value} failed: {e}")
                outcome = None
                success = False
        else:
            logger.warning(f"No controller for action type: {action_type.value}")
            outcome = None
            success = False
            
        # Record action
        self.action_history.append((action, outcome, success))
        
        # Update active loops
        self._update_active_loops(action, outcome, success)
        
        return success, outcome
        
    def start_loop(self, perception: SensoryInput) -> SensorimotorLoop:
        """
        Start a new perception-action loop.
        
        Args:
            perception: Initial perception
            
        Returns:
            New sensorimotor loop
        """
        # Extract features
        features = self._extract_features(perception)
        
        # Determine possible actions
        possible_actions = self._get_possible_actions(features)
        
        # Create loop
        loop = SensorimotorLoop(
            perception=perception,
            processing={'features': features, 'possible_actions': possible_actions},
            action=None  # To be filled when action is chosen
        )
        
        self.active_loops.append(loop)
        return loop
        
    def complete_loop(self, loop: SensorimotorLoop, action: MotorAction,
                     outcome: Any, success: bool):
        """Complete a sensorimotor loop with results."""
        loop.action = action
        loop.outcome = outcome
        loop.success = success
        
        # Learn from this loop
        self._learn_from_loop(loop)
        
        # Remove from active loops
        if loop in self.active_loops:
            self.active_loops.remove(loop)
            
    def get_affordances(self, current_perception: SensoryInput) -> List[AffordancePattern]:
        """
        Get available affordances given current perception.
        
        Returns:
            List of applicable affordance patterns
        """
        features = self._extract_features(current_perception)
        applicable = []
        
        for affordance in self.affordances.values():
            if self._matches_perception_pattern(features, affordance.perception_features):
                applicable.append(affordance)
                
        # Sort by success rate
        return sorted(applicable, key=lambda a: a.success_rate, reverse=True)
        
    def coordinate_multimodal(self, inputs: List[SensoryInput]) -> Dict[str, Any]:
        """
        Coordinate multiple sensory inputs into coherent understanding.
        
        Args:
            inputs: List of sensory inputs from different modalities
            
        Returns:
            Integrated perception
        """
        integrated = {
            'modalities': {},
            'features': {},
            'conflicts': [],
            'synthesis': None
        }
        
        # Process each modality
        for input_data in inputs:
            modality = input_data.sensor_type.value
            features = self._extract_features(input_data)
            integrated['modalities'][modality] = features
            
            # Merge features
            for key, value in features.items():
                if key in integrated['features']:
                    # Detect conflicts
                    if integrated['features'][key] != value:
                        integrated['conflicts'].append({
                            'feature': key,
                            'values': [integrated['features'][key], value],
                            'modalities': ['previous', modality]
                        })
                else:
                    integrated['features'][key] = value
                    
        # Synthesize understanding
        integrated['synthesis'] = self._synthesize_multimodal(integrated['modalities'])
        
        return integrated
        
    def motor_babbling(self, environment: Any, max_actions: int = 10) -> List[Dict[str, Any]]:
        """
        Explore environment through random actions (like infant motor babbling).
        
        Args:
            environment: Environment to explore
            max_actions: Maximum number of exploratory actions
            
        Returns:
            List of discoveries
        """
        discoveries = []
        
        for i in range(max_actions):
            # Random action selection
            action_type = np.random.choice(list(ActionType))
            
            # Generate random parameters based on action type
            parameters = self._generate_random_parameters(action_type)
            
            # Try the action
            success, outcome = self.act(action_type, parameters)
            
            # Record discovery
            discovery = {
                'action': action_type.value,
                'parameters': parameters,
                'success': success,
                'outcome': str(outcome)[:100] if outcome else None,
                'affordance_learned': False
            }
            
            # Check if we learned a new affordance
            if success and len(self.affordances) > len(discoveries):
                discovery['affordance_learned'] = True
                
            discoveries.append(discovery)
            
        return discoveries
        
    def get_motor_plan(self, goal: Dict[str, Any], 
                      current_state: Dict[str, Any]) -> List[MotorAction]:
        """
        Create a motor plan to achieve a goal from current state.
        
        Args:
            goal: Desired end state
            current_state: Current state
            
        Returns:
            Sequence of motor actions
        """
        plan = []
        
        # Simple planning - can be made more sophisticated
        # Identify differences
        differences = self._compute_state_difference(current_state, goal)
        
        # For each difference, find action to address it
        for diff_type, diff_value in differences.items():
            action_type = self._select_action_for_difference(diff_type)
            if action_type:
                parameters = self._parameterize_action(action_type, diff_value)
                plan.append(MotorAction(
                    action_type=action_type,
                    parameters=parameters,
                    expected_outcome=diff_value
                ))
                
        return plan
        
    def _extract_features(self, perception: SensoryInput) -> Dict[str, Any]:
        """Extract features from perception."""
        if perception.sensor_type in self.feature_extractors:
            return self.feature_extractors[perception.sensor_type](perception.data)
        return {'raw_data': str(perception.data)[:100]}
        
    def _get_possible_actions(self, features: Dict[str, Any]) -> List[ActionType]:
        """Determine possible actions given features."""
        possible = []
        
        # Check each action's applicability
        for action_type in ActionType:
            if self._is_action_applicable(action_type, features):
                possible.append(action_type)
                
        return possible
        
    def _update_affordances(self, perception: SensoryInput):
        """Update affordance patterns based on new perception."""
        features = self._extract_features(perception)
        
        # Look at recent actions
        if self.action_history:
            recent_action, outcome, success = self.action_history[-1]
            
            if success:
                # Create or update affordance
                affordance_key = f"{perception.sensor_type.value}_{recent_action.action_type.value}"
                
                if affordance_key in self.affordances:
                    affordance = self.affordances[affordance_key]
                    affordance.usage_count += 1
                    # Update success rate
                    affordance.success_rate = (
                        affordance.success_rate * (affordance.usage_count - 1) + 1.0
                    ) / affordance.usage_count
                else:
                    # New affordance
                    self.affordances[affordance_key] = AffordancePattern(
                        name=affordance_key,
                        perception_features=features,
                        possible_actions=[recent_action.action_type],
                        success_rate=1.0,
                        usage_count=1
                    )
                    
    def _update_active_loops(self, action: MotorAction, outcome: Any, success: bool):
        """Update active sensorimotor loops."""
        # Find loops that might be completed by this action
        for loop in self.active_loops:
            if loop.action is None:
                # Check if this action fits the loop
                if action.action_type in loop.processing.get('possible_actions', []):
                    self.complete_loop(loop, action, outcome, success)
                    break
                    
    def _learn_from_loop(self, loop: SensorimotorLoop):
        """Learn from completed sensorimotor loop."""
        if not loop.success:
            return
            
        # Update or create affordance
        features = loop.processing.get('features', {})
        affordance_key = f"{loop.perception.sensor_type.value}_{loop.action.action_type.value}"
        
        if affordance_key in self.affordances:
            self.affordances[affordance_key].usage_count += 1
        else:
            self.affordances[affordance_key] = AffordancePattern(
                name=affordance_key,
                perception_features=features,
                possible_actions=[loop.action.action_type],
                success_rate=1.0,
                usage_count=1
            )
            
    # Sensory processors
    def _process_textual(self, data: Any) -> Dict[str, Any]:
        """Process textual sensory input."""
        text = str(data)
        return {
            'length': len(text),
            'words': len(text.split()),
            'has_code': any(kw in text for kw in ['def', 'class', 'import', 'function']),
            'has_numbers': any(c.isdigit() for c in text)
        }
        
    def _process_visual(self, data: Any) -> Dict[str, Any]:
        """Process visual sensory input."""
        # Placeholder for visual processing
        return {'type': 'visual', 'processed': True}
        
    def _process_numeric(self, data: Any) -> Dict[str, Any]:
        """Process numeric sensory input."""
        try:
            values = list(data) if hasattr(data, '__iter__') else [data]
            return {
                'count': len(values),
                'mean': np.mean(values) if values else 0,
                'range': (min(values), max(values)) if values else (0, 0)
            }
        except:
            return {'type': 'numeric', 'error': 'processing_failed'}
            
    def _process_structured(self, data: Any) -> Dict[str, Any]:
        """Process structured sensory input."""
        return {
            'type': type(data).__name__,
            'has_len': hasattr(data, '__len__'),
            'has_iter': hasattr(data, '__iter__')
        }
        
    # Motor controllers
    def _control_read(self, parameters: Dict[str, Any]) -> Any:
        """Control read action."""
        # Placeholder implementation
        return f"Read from {parameters.get('source', 'unknown')}"
        
    def _control_write(self, parameters: Dict[str, Any]) -> Any:
        """Control write action."""
        # Placeholder implementation
        return f"Wrote to {parameters.get('target', 'unknown')}"
        
    def _control_transform(self, parameters: Dict[str, Any]) -> Any:
        """Control transform action."""
        # Placeholder implementation
        return f"Transformed using {parameters.get('operation', 'unknown')}"
        
    def _control_query(self, parameters: Dict[str, Any]) -> Any:
        """Control query action."""
        # Placeholder implementation
        return f"Queried for {parameters.get('query', 'unknown')}"
        
    # Feature extractors
    def _extract_text_features(self, data: Any) -> Dict[str, Any]:
        """Extract features from text."""
        text = str(data)
        return {
            'length': len(text),
            'type': 'code' if any(kw in text for kw in ['def', 'class']) else 'text',
            'complexity': len(set(text.split()))  # Unique words
        }
        
    def _extract_visual_features(self, data: Any) -> Dict[str, Any]:
        """Extract features from visual data."""
        return {'modality': 'visual'}
        
    def _extract_numeric_features(self, data: Any) -> Dict[str, Any]:
        """Extract features from numeric data."""
        return {'modality': 'numeric', 'dimensionality': 1}
        
    # Helper methods
    def _matches_expectation(self, outcome: Any, expected: Any) -> bool:
        """Check if outcome matches expectation."""
        # Simple equality check - can be made more sophisticated
        return outcome == expected
        
    def _matches_perception_pattern(self, features: Dict[str, Any],
                                  pattern: Dict[str, Any]) -> bool:
        """Check if features match a perception pattern."""
        for key, value in pattern.items():
            if key not in features or features[key] != value:
                return False
        return True
        
    def _synthesize_multimodal(self, modalities: Dict[str, Dict[str, Any]]) -> str:
        """Synthesize understanding from multiple modalities."""
        # Simple synthesis - can be made more sophisticated
        return f"Integrated perception from {len(modalities)} modalities"
        
    def _generate_random_parameters(self, action_type: ActionType) -> Dict[str, Any]:
        """Generate random parameters for motor babbling."""
        if action_type == ActionType.READ:
            return {'source': f'random_source_{np.random.randint(100)}'}
        elif action_type == ActionType.WRITE:
            return {'target': f'random_target_{np.random.randint(100)}'}
        else:
            return {'param': np.random.random()}
            
    def _compute_state_difference(self, current: Dict[str, Any],
                                goal: Dict[str, Any]) -> Dict[str, Any]:
        """Compute difference between states."""
        diff = {}
        for key, goal_value in goal.items():
            if key not in current or current[key] != goal_value:
                diff[key] = goal_value
        return diff
        
    def _select_action_for_difference(self, diff_type: str) -> Optional[ActionType]:
        """Select action to address a difference."""
        # Simple mapping - can be made more sophisticated
        if 'write' in diff_type or 'create' in diff_type:
            return ActionType.WRITE
        elif 'read' in diff_type or 'get' in diff_type:
            return ActionType.READ
        elif 'transform' in diff_type or 'change' in diff_type:
            return ActionType.TRANSFORM
        else:
            return ActionType.QUERY
            
    def _parameterize_action(self, action_type: ActionType,
                           target_value: Any) -> Dict[str, Any]:
        """Create parameters for an action."""
        return {
            'action': action_type.value,
            'target': target_value
        }
        
    def _is_action_applicable(self, action_type: ActionType,
                            features: Dict[str, Any]) -> bool:
        """Check if an action is applicable given features."""
        # Simple applicability rules
        if action_type == ActionType.READ:
            return True  # Can always try to read
        elif action_type == ActionType.WRITE:
            return 'length' in features  # Need something to write
        else:
            return True