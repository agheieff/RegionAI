# DESIGN-XV: Symbolic Language Engine Architecture

## 1. Vision & Goal

### Long-Term Vision
To create a symbolic reasoning system that can understand natural language from first principles, pushing this approach to its empirical limits. This system will bridge the gap between human linguistic expression and machine-comprehensible knowledge representations without relying on massive pre-trained models, instead building understanding through compositional symbolic reasoning.

### Immediate Goal
To build an engine that can parse natural language utterances into a structured WorldKnowledgeGraph in a computationally tractable way, achieving O(n) complexity through strategic use of lazy evaluation, bounded search, and intelligent caching.

## 2. Core Principles (The "Containment Tricks")

### 2.1 Lazy Region Evaluation

**Principle**: Represent linguistic structures as unresolved `SymbolicConstraints` and only ground them when demanded by a reasoning step.

**Key Insights**:
- Natural language is inherently ambiguous and context-dependent
- Full resolution of all possible meanings is computationally intractable
- Most linguistic units remain unresolved in human comprehension until needed

**Implementation Strategy**:
- Store phrases as constraint objects containing:
  - The raw text
  - Syntactic structure (from POS tagging)
  - A promise to compute semantic candidates when needed
- Resolution triggered only by:
  - Direct query about the constraint
  - Reasoning that requires the constraint's meaning
  - Disambiguation requirements from context

**Benefits**:
- Avoids exponential explosion of meaning combinations
- Allows incremental understanding as more context becomes available
- Mirrors human cognitive processing of language

### 2.2 Beam-Width Disambiguation

**Principle**: Use beam search with configurable width `k` to manage ambiguity, keeping only the top `k` most probable interpretations for any given phrase.

**Key Insights**:
- Complete enumeration of all possible meanings is neither necessary nor desirable
- A small number of high-probability candidates usually suffices
- Probability can be estimated from multiple sources (frequency, context, syntactic fit)

**Implementation Strategy**:
- For each `SymbolicConstraint`, maintain at most `k` `RegionCandidate` objects
- Score candidates based on:
  - Concept frequency in the knowledge graph
  - Syntactic compatibility with surrounding constraints
  - Semantic coherence with resolved neighbors
- Dynamically adjust beam width based on:
  - Available computational resources
  - Required precision for the task
  - Measured ambiguity of the input

**Benefits**:
- Bounds computational complexity to O(k×n) where k is small and fixed
- Provides probabilistic reasoning about interpretations
- Allows trading off between speed and accuracy

### 2.3 Clause-Local Memoization

**Principle**: Cache computed results of previously seen phrases to avoid redundant work, with cache scope limited to syntactic boundaries.

**Key Insights**:
- Language exhibits massive redundancy at the phrase level
- Common phrases have stable meanings within similar contexts
- Cache invalidation can follow syntactic boundaries

**Implementation Strategy**:
- Maintain a phrase cache mapping:
  - Key: (phrase_text, syntactic_context) → Value: List[RegionCandidate]
- Cache scope rules:
  - Clear cache at sentence boundaries by default
  - Extend cache across sentences for noun phrases
  - Special handling for pronouns and references
- Cache warming strategies:
  - Pre-compute common phrases
  - Learn frequent patterns from usage
  - Share cache across similar documents

**Benefits**:
- Dramatic speedup for common linguistic patterns
- Bounded memory usage through scope limits
- Enables learning through usage patterns

## 3. Key Data Structures

### 3.1 SymbolicConstraint

```python
@dataclass
class SymbolicConstraint:
    """Represents an unresolved linguistic unit."""
    
    # Core identification
    constraint_id: str
    raw_text: str
    span: Tuple[int, int]  # Character positions in source
    
    # Syntactic information
    pos_tags: List[str]
    dependency_role: Optional[str]
    head_constraint: Optional['SymbolicConstraint']
    
    # Semantic candidates (lazy-loaded)
    _candidates: Optional[List['RegionCandidate']] = None
    _resolution_requested: bool = False
    
    # Structural relationships
    children: List['SymbolicConstraint'] = field(default_factory=list)
    modifiers: List['SymbolicConstraint'] = field(default_factory=list)
    
    # Memoization support
    cache_key: Optional[str] = None
    last_resolution_time: Optional[float] = None
```

### 3.2 RegionCandidate

```python
@dataclass
class RegionCandidate:
    """One possible meaning for a constraint."""
    
    # Identity
    candidate_id: str
    source_constraint: SymbolicConstraint
    
    # Semantic content
    concepts: List[Concept]  # Existing or new concepts
    relations: List[Tuple[Concept, Relation, Concept]]
    properties: Dict[str, Any]
    
    # Scoring and probability
    base_score: float  # From frequency, syntax fit
    context_score: float = 0.0  # From surrounding constraints
    total_score: float = field(init=False)
    
    # Region embedding (lazy-computed)
    _region_embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        self.total_score = self.base_score + self.context_score
```

### 3.3 ParseTree

```python
@dataclass
class ParseTree:
    """Hierarchical structure of constraints representing a sentence."""
    
    # Identity
    tree_id: str
    source_text: str
    
    # Structure
    root_constraint: SymbolicConstraint
    all_constraints: Dict[str, SymbolicConstraint]
    
    # Metadata
    parse_timestamp: float
    spacy_doc: Optional[Doc] = None  # Original spaCy parse
    
    # Resolution state
    resolution_status: Dict[str, bool] = field(default_factory=dict)
    resolution_order: List[str] = field(default_factory=list)
    
    # Graph integration
    graph_nodes: Dict[str, Concept] = field(default_factory=dict)
    graph_relations: List[Tuple[Concept, Relation, Concept]] = field(default_factory=list)
```

## 4. High-Level Pipeline Flow

### Input
A raw string of text (e.g., "The cat, which was on the mat, ate the fish.")

### Step 1: Tokenization & POS Tagging
- **Tool**: spaCy with en_core_web_sm model
- **Process**:
  1. Tokenize text into words and punctuation
  2. Assign part-of-speech tags
  3. Build dependency parse tree
  4. Identify syntactic chunks (noun phrases, verb phrases)
- **Output**: Annotated spaCy Doc object

### Step 2: Candidate Generation
- **Process**:
  1. For each noun phrase:
     - Check memoization cache
     - If not cached:
       - Search existing concepts by name similarity
       - Generate new concept candidates if needed
       - Score based on frequency and context
       - Keep top k candidates
  2. For each verb phrase:
     - Identify action concepts
     - Generate relation candidates
     - Score based on argument compatibility
  3. For modifiers:
     - Create property candidates
     - Link to modified constraints
- **Output**: Beam of RegionCandidate objects per constraint

### Step 3: Constraint Construction
- **Process**:
  1. Create root SymbolicConstraint for main clause
  2. Recursively create child constraints following dependency tree
  3. Link constraints bidirectionally (parent ↔ child)
  4. Mark special constructions:
     - Relative clauses
     - Conjunctions
     - Comparisons
  5. Assign cache keys based on text and syntactic context
- **Output**: Complete ParseTree with nested constraints

### Step 4: Storage
- **Process**:
  1. Generate unique ID for ParseTree
  2. Store unresolved tree in WorldKnowledgeGraph:
     ```
     Utterance node → HAS_PARSE → ParseTree node
     ParseTree node → HAS_CONSTRAINT → SymbolicConstraint nodes
     ```
  3. Create placeholder nodes for unresolved concepts
  4. Index by:
     - Source text
     - Timestamp
     - Syntactic patterns
  5. Update memoization cache with stable resolutions
- **Output**: Persistent, queryable representation in knowledge graph

### Example Processing

**Input**: "The cat, which was on the mat, ate the fish."

**After Step 1** (spaCy):
```
The/DT cat/NN ,/, which/WDT was/VBD on/IN the/DT mat/NN ,/, ate/VBD the/DT fish/NN ./.
```

**After Step 2** (Candidates):
```
"cat" → [
  RegionCandidate(concepts=[Concept("Cat")], score=0.9),
  RegionCandidate(concepts=[Concept("Feline")], score=0.7)
]
"mat" → [
  RegionCandidate(concepts=[Concept("Mat")], score=0.8),
  RegionCandidate(concepts=[Concept("FloorCovering")], score=0.6)
]
```

**After Step 3** (Constraints):
```
ParseTree(
  root=SymbolicConstraint("ate", children=[
    SymbolicConstraint("cat", modifiers=[
      SymbolicConstraint("which was on the mat")
    ]),
    SymbolicConstraint("fish")
  ])
)
```

**After Step 4** (Storage):
```
Graph nodes:
- Utterance_001 → HAS_PARSE → ParseTree_001
- ParseTree_001 → HAS_ROOT → Constraint_ate
- Constraint_ate → HAS_SUBJECT → Constraint_cat
- Constraint_ate → HAS_OBJECT → Constraint_fish
- Constraint_cat → HAS_MODIFIER → Constraint_which_clause
```

## 5. Performance Characteristics

### Time Complexity
- **Tokenization**: O(n) where n is text length
- **Candidate Generation**: O(n × k) where k is beam width
- **Constraint Construction**: O(n) tree traversal
- **Storage**: O(n) graph operations
- **Total**: O(n × k) ≈ O(n) for fixed small k

### Space Complexity
- **Parse structures**: O(n)
- **Candidate beams**: O(n × k)
- **Memoization cache**: O(m) where m is unique phrases
- **Total**: O(n + m) with m bounded by cache policy

### Scalability Strategies
1. **Distributed parsing**: Process documents in parallel
2. **Shared memoization**: Centralized cache across workers
3. **Incremental resolution**: Process constraints on demand
4. **Adaptive beam width**: Reduce k for simple text
5. **Cache warming**: Pre-compute common patterns

## 6. Future Extensions

### 6.1 Context-Aware Resolution
- Use surrounding resolved constraints to influence scoring
- Implement coherence metrics across constraints
- Learn context patterns from usage

### 6.2 Interactive Disambiguation
- Query user when confidence is low
- Learn from disambiguation choices
- Build user-specific interpretation models

### 6.3 Cross-Linguistic Support
- Abstract constraint types from English-specific features
- Support morphologically rich languages
- Handle non-configurational word order

### 6.4 Reasoning Integration
- Trigger resolution based on reasoning needs
- Use reasoning results to update scores
- Implement explanation generation

## 7. Implementation Roadmap

### Phase 1: Core Infrastructure (2 weeks)
- Implement basic data structures
- Set up spaCy integration
- Create simple memoization cache

### Phase 2: Candidate Generation (3 weeks)
- Build concept matching algorithms
- Implement scoring functions
- Create beam search manager

### Phase 3: Constraint Construction (2 weeks)
- Parse tree to constraint converter
- Relationship extraction
- Modifier attachment

### Phase 4: Graph Integration (2 weeks)
- Storage layer implementation
- Query interface
- Cache persistence

### Phase 5: Optimization & Testing (3 weeks)
- Performance profiling
- Cache tuning
- Comprehensive test suite

## Conclusion

This design represents a fundamental shift in how RegionAI approaches natural language understanding. By combining lazy evaluation, bounded search, and intelligent caching, we can process language in a way that is both computationally tractable and cognitively plausible. The symbolic approach, enhanced with these containment tricks, promises to deliver interpretable, efficient, and scalable language understanding that can serve as the foundation for true natural language reasoning.