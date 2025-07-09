# Document 1: The Language Bridge
## Architecture and Methodology for Natural Language to RegionAI Mapping

### Executive Summary

This document defines the architecture for bridging natural language to RegionAI's grounded functional concepts. The proposed system creates a bidirectional mapping between the ambiguity of human language and the precision of discovered computational primitives, enabling RegionAI to understand specifications, generate code, and explain its reasoning in natural terms.

### 1. Proposed Architecture

#### 1.1 Overview: The Dual-AST Approach

The core insight of our architecture is that natural language and functional computation share a fundamental property: they are both compositional. Just as complex programs decompose into primitive operations, complex utterances decompose into primitive meanings. We propose a dual-AST architecture that leverages this parallel structure.

```
Natural Language Input
        ↓
[Linguistic Parser]
        ↓
Linguistic AST
        ↓
[Semantic Transformer]
        ↓
Functional AST
        ↓
[RegionAI Discovery Engine]
        ↓
Implementation
```

#### 1.2 Layer 1: Linguistic AST Construction

The Linguistic AST represents the grammatical and semantic structure of natural language input. Unlike traditional parse trees that focus on syntax, our Linguistic AST captures semantic intent.

**Example:**
Input: "Calculate the average score for each student"

```
LinguisticAST(
  action: Calculate(
    target: Average(
      of: Score
    ),
    grouping: ForEach(
      entity: Student
    )
  )
)
```

**Key Components:**

1. **Action Nodes**: Represent verbs and their intent (Calculate, Find, Create, Transform)
2. **Entity Nodes**: Represent nouns and data structures (Student, Score, List)
3. **Modifier Nodes**: Represent adjectives and constraints (Average, Maximum, Positive)
4. **Relation Nodes**: Represent prepositions and relationships (ForEach, Of, With)

#### 1.3 Layer 2: Semantic Transformation

The Semantic Transformer maps Linguistic AST nodes to Functional AST nodes using learned correspondences. This is where ambiguity resolution occurs.

**Transformation Rules (Examples):**

```
Calculate(Average(X)) → REDUCE(X, MEAN)
ForEach(Entity) → GROUP_BY(Entity.id)
Find(Maximum(X)) → REDUCE(X, MAX)
Filter(Positive(X)) → FILTER(X, GREATER_THAN(0))
```

**Key Innovation: Contextual Region Embeddings**

Each linguistic concept maps to a region in the same high-dimensional space as RegionAI's functional primitives. The transformation process finds the nearest functional regions to linguistic regions.

```python
class SemanticTransformer:
    def __init__(self, linguistic_embeddings, functional_embeddings):
        self.ling_space = linguistic_embeddings
        self.func_space = functional_embeddings
        self.alignment = self.learn_alignment()
    
    def transform(self, linguistic_ast):
        # Map each linguistic node to functional space
        functional_nodes = []
        for node in linguistic_ast.traverse():
            ling_region = self.ling_space.encode(node)
            func_region = self.alignment.project(ling_region)
            functional_primitive = self.func_space.nearest(func_region)
            functional_nodes.append(functional_primitive)
        
        # Compose functional AST maintaining structure
        return self.compose_functional_ast(functional_nodes)
```

#### 1.4 Layer 3: Functional AST Generation

The Functional AST uses RegionAI's discovered primitives as nodes. This is the executable representation.

**Example Transformation:**
```
Linguistic: Calculate(Average(Score), ForEach(Student))
                            ↓
Functional: COMPOSE(
  GROUP_BY('student_id'),
  MAP(
    COMPOSE(
      MAP_GET('score'),
      REDUCE(MEAN)
    )
  )
)
```

#### 1.5 Ambiguity Resolution Through Region Overlap

When linguistic regions map to multiple functional regions, we use several strategies:

1. **Context Expansion**: Include surrounding linguistic context to narrow the functional mapping
2. **Type Constraints**: Use inferred types to eliminate incompatible mappings
3. **Precedence Learning**: Learn from training data which mappings are most common
4. **Interactive Clarification**: When confidence is low, generate clarifying questions

#### 1.6 Bidirectional Flow: Explanation Generation

The architecture supports reverse transformation for explanation:

```
Functional AST → Linguistic AST → Natural Language
```

This enables RegionAI to explain discovered patterns in human terms.

### 2. The First Target Domain

#### 2.1 Domain Analysis Framework

To select the optimal first domain, we evaluate candidates across five dimensions:

1. **Linguistic Complexity**: Range and ambiguity of language used
2. **Functional Coverage**: How well it exercises RegionAI's primitives
3. **Data Availability**: Quality and quantity of training examples
4. **Practical Value**: Immediate usefulness of the capability
5. **Generalization Potential**: Foundation for broader capabilities

#### 2.2 Candidate Domain 1: Technical API Documentation

**Description**: Documentation for software APIs, including function descriptions, parameter explanations, and usage examples.

**Analysis**:
- **Linguistic Complexity**: LOW-MEDIUM
  - Highly structured, formulaic language
  - Technical jargon but limited ambiguity
  - Clear input-output specifications
  
- **Functional Coverage**: HIGH
  - Direct mappings to code operations
  - Covers full range of data transformations
  - Includes error handling and edge cases
  
- **Data Availability**: EXCELLENT
  - Massive corpus from open-source projects
  - High-quality, peer-reviewed content
  - Structured format aids parsing
  
- **Practical Value**: HIGH
  - Immediate application in code generation
  - Valuable for documentation generation
  - Enhances developer productivity
  
- **Generalization Potential**: MEDIUM
  - Limited to technical domain
  - Doesn't exercise full ambiguity resolution
  - May create overly rigid mappings

**Score**: 4.0/5.0

#### 2.3 Candidate Domain 2: Simple Children's Stories

**Description**: Basic narrative texts written for early readers, featuring simple plots and clear causality.

**Analysis**:
- **Linguistic Complexity**: LOW
  - Limited vocabulary
  - Simple sentence structures
  - Minimal ambiguity
  
- **Functional Coverage**: LOW
  - Primarily sequential actions
  - Limited data transformation
  - Focus on narrative rather than computation
  
- **Data Availability**: GOOD
  - Large corpus of public domain stories
  - Well-structured and annotated
  - Multiple complexity levels available
  
- **Practical Value**: LOW
  - No immediate practical application
  - Primarily educational value
  - Limited relevance to RegionAI's core purpose
  
- **Generalization Potential**: LOW-MEDIUM
  - Teaches basic causality and sequence
  - Too simple for complex reasoning
  - May not transfer to technical domains

**Score**: 2.0/5.0

#### 2.4 Candidate Domain 3: Data Processing Specifications

**Description**: Natural language descriptions of data transformation tasks, such as "filter customers by age and calculate average purchase amount."

**Analysis**:
- **Linguistic Complexity**: MEDIUM
  - Mix of technical and business language
  - Moderate ambiguity in specifications
  - Multiple valid interpretations common
  
- **Functional Coverage**: EXCELLENT
  - Direct mapping to MAP, FILTER, REDUCE
  - Exercises composition and pipelines
  - Includes conditional logic and aggregation
  
- **Data Availability**: GOOD
  - Can generate from existing SQL/code
  - Business requirements documents
  - Stack Overflow questions
  
- **Practical Value**: EXCELLENT
  - Immediate application in data analysis
  - Valuable for business intelligence
  - Automates common developer tasks
  
- **Generalization Potential**: HIGH
  - Foundation for general programming
  - Teaches composition and data flow
  - Natural progression to complex algorithms

**Score**: 4.5/5.0

#### 2.5 Recommendation: Data Processing Specifications

After careful analysis, I recommend **Data Processing Specifications** as the first target domain for the following reasons:

1. **Optimal Complexity Balance**: Complex enough to be meaningful, simple enough to be tractable
2. **Direct Primitive Mapping**: Leverages RegionAI's existing strengths in data transformation
3. **Progressive Difficulty**: Natural curriculum from simple filters to complex pipelines
4. **Immediate Utility**: Solves real problems from day one
5. **Strong Foundation**: Skills transfer directly to general programming

#### 2.6 Implementation Strategy for Chosen Domain

**Phase 1: Simple Operations (Months 1-2)**
- Single-primitive mappings: "sort the list" → SORT
- Basic parameters: "get the name field" → MAP_GET('name')
- Simple compositions: "sum the values" → MAP_GET + SUM

**Phase 2: Composite Operations (Months 3-4)**
- Multi-step pipelines: "get positive values and sum them"
- Conditional logic: "if age > 18, mark as adult"
- Basic aggregations: "group by category and count"

**Phase 3: Complex Specifications (Months 5-6)**
- Nested operations: "for each department, find the highest-paid employee"
- Multiple conditions: "filter by age and location, then sort by score"
- Statistical operations: "calculate standard deviation by group"

**Expected Outcomes**:
- 90%+ accuracy on simple operations
- 75%+ accuracy on composite operations
- 60%+ accuracy on complex specifications
- Foundation for natural language programming

### 3. Curriculum Design

#### 3.1 Overview: Progressive Complexity Through Five Stages

The curriculum for Data Processing Specifications follows a carefully crafted progression, where each stage builds upon the previous while introducing exactly one new conceptual challenge. This ensures stable learning and clear diagnostic capability when issues arise.

#### 3.2 Stage 1: Simple Filtering & Mapping (Weeks 1-2)

**Conceptual Focus**: Single-primitive operations with direct parameter mapping

**Example Tasks**:
1. "Find all users over 30"
   - Linguistic AST: `Find(All(Users), Where(Age > 30))`
   - Functional AST: `FILTER(users, GREATER_THAN(GET_FIELD('age'), 30))`

2. "Get the names of all products"
   - Linguistic AST: `Get(Names, Of(All(Products)))`
   - Functional AST: `MAP(products, GET_FIELD('name'))`

3. "Select active accounts"
   - Linguistic AST: `Select(Accounts, Where(Status = Active))`
   - Functional AST: `FILTER(accounts, EQUALS(GET_FIELD('status'), 'active'))`

**Learning Objectives**:
- Map action verbs to functional primitives
- Extract field names from linguistic context
- Handle simple comparison operators
- Recognize entity plurals as collections

**Success Criteria**: 95% accuracy on unseen examples within this complexity class

#### 3.3 Stage 2: Simple Aggregation (Weeks 3-4)

**Conceptual Focus**: Reduction operations and basic statistical functions

**Example Tasks**:
1. "Calculate the total sales"
   - Linguistic AST: `Calculate(Total(Sales))`
   - Functional AST: `REDUCE(sales, SUM)`

2. "Find the maximum temperature"
   - Linguistic AST: `Find(Maximum(Temperature))`
   - Functional AST: `REDUCE(temperatures, MAX)`

3. "Count the number of orders"
   - Linguistic AST: `Count(Number(Of(Orders)))`
   - Functional AST: `REDUCE(orders, COUNT)`

**Learning Objectives**:
- Map aggregation words to reduction primitives
- Understand implicit field selection in context
- Handle statistical terminology
- Recognize when collection-wide operations are needed

**Success Criteria**: 90% accuracy, with clear understanding of when to apply REDUCE vs MAP

#### 3.4 Stage 3: Compositional Logic (Weeks 5-6)

**Conceptual Focus**: Multi-step operations requiring function composition

**Example Tasks**:
1. "Find the average score of all active students"
   - Linguistic AST: `Find(Average(Score), Of(Students, Where(Status = Active)))`
   - Functional AST: `COMPOSE(
       FILTER(students, EQUALS(GET_FIELD('status'), 'active')),
       MAP(GET_FIELD('score')),
       REDUCE(MEAN)
     )`

2. "Get the names of products under $50"
   - Linguistic AST: `Get(Names, Of(Products, Where(Price < 50)))`
   - Functional AST: `COMPOSE(
       FILTER(products, LESS_THAN(GET_FIELD('price'), 50)),
       MAP(GET_FIELD('name'))
     )`

3. "Calculate total revenue from premium customers"
   - Linguistic AST: `Calculate(Total(Revenue), From(Customers, Where(Type = Premium)))`
   - Functional AST: `COMPOSE(
       FILTER(customers, EQUALS(GET_FIELD('type'), 'premium')),
       MAP(GET_FIELD('revenue')),
       REDUCE(SUM)
     )`

**Learning Objectives**:
- Decompose complex requests into primitive sequences
- Maintain correct operation ordering
- Handle nested constraints
- Recognize implicit data flow

**Success Criteria**: 85% accuracy, with correct operation ordering in 95% of cases

#### 3.5 Stage 4: Conditional Logic (Weeks 7-8)

**Conceptual Focus**: Branching logic and conditional transformations

**Example Tasks**:
1. "If a user is an admin, get their email; otherwise, get their ID"
   - Linguistic AST: `Conditional(
       If(User.Type = Admin),
       Then(Get(Email)),
       Else(Get(ID))
     )`
   - Functional AST: `MAP(users, 
       IF_THEN_ELSE(
         EQUALS(GET_FIELD('type'), 'admin'),
         GET_FIELD('email'),
         GET_FIELD('id')
       )
     )`

2. "Apply a 20% discount to items over $100"
   - Linguistic AST: `Apply(Discount(20%), To(Items, Where(Price > 100)))`
   - Functional AST: `MAP(items,
       IF_THEN_ELSE(
         GREATER_THAN(GET_FIELD('price'), 100),
         MULTIPLY(GET_FIELD('price'), 0.8),
         GET_FIELD('price')
       )
     )`

3. "Mark orders as urgent if value exceeds $1000 or customer is VIP"
   - Linguistic AST: `Mark(Orders, As(Urgent), If(Value > 1000 OR Customer.Type = VIP))`
   - Functional AST: `MAP(orders,
       SET_FIELD('urgent',
         OR(
           GREATER_THAN(GET_FIELD('value'), 1000),
           EQUALS(GET_FIELD('customer_type'), 'VIP')
         )
       )
     )`

**Learning Objectives**:
- Recognize conditional language patterns
- Map if/then/else to functional conditionals
- Handle boolean logic operators
- Understand field mutations vs queries

**Success Criteria**: 80% accuracy, with correct boolean logic in 90% of cases

#### 3.6 Stage 5: Multi-Step Pipelines (Weeks 9-10)

**Conceptual Focus**: Complex data processing workflows with multiple transformations

**Example Tasks**:
1. "Filter for all products in the 'electronics' category, apply a 10% discount, and then return the names of those under $500"
   - Linguistic AST: `Pipeline(
       Filter(Products, Where(Category = Electronics)),
       Apply(Discount(10%)),
       Filter(Where(Price < 500)),
       Return(Names)
     )`
   - Functional AST: `COMPOSE(
       FILTER(products, EQUALS(GET_FIELD('category'), 'electronics')),
       MAP(LAMBDA(p: SET_FIELD(p, 'price', MULTIPLY(GET_FIELD(p, 'price'), 0.9)))),
       FILTER(LESS_THAN(GET_FIELD('price'), 500)),
       MAP(GET_FIELD('name'))
     )`

2. "Group customers by region, calculate average purchase per region, then sort by highest average"
   - Linguistic AST: `Pipeline(
       Group(Customers, By(Region)),
       Calculate(Average(Purchase), PerGroup),
       Sort(By(Average), Descending)
     )`
   - Functional AST: `COMPOSE(
       GROUP_BY(customers, GET_FIELD('region')),
       MAP_GROUPS(LAMBDA(group: {
         'region': GET_FIELD(FIRST(group), 'region'),
         'avg_purchase': REDUCE(MAP(group, GET_FIELD('purchase')), MEAN)
       })),
       SORT_BY(GET_FIELD('avg_purchase'), DESCENDING)
     )`

**Learning Objectives**:
- Maintain context through long pipelines
- Handle stateful transformations
- Recognize implicit intermediate results
- Manage complex data shapes

**Success Criteria**: 75% accuracy on full pipelines, 90% accuracy on individual steps

#### 3.7 Curriculum Evaluation and Adaptation

**Continuous Assessment**:
- Track error patterns at each stage
- Identify systematic misunderstandings
- Adjust curriculum based on failure modes

**Remedial Loops**:
- When accuracy drops below threshold, generate targeted exercises
- Focus on specific primitive combinations causing errors
- Use error analysis to improve linguistic embeddings

### 4. Handling Ambiguity

#### 4.1 The Region-Based Resolution Framework

Ambiguity in natural language maps to overlapping regions in our embedding space. The key insight is that context acts as a geometric constraint, narrowing the intersection of possible meanings to identify the intended interpretation.

#### 4.2 Example 1: Lexical Ambiguity - "Mean"

**Input**: "Calculate the mean score" vs "Filter out mean comments"

**Region Analysis**:

1. **"mean" in statistical context**:
   - Linguistic embedding activates regions near: [average, statistical, mathematical]
   - Contextual words "calculate" and "score" reinforce statistical interpretation
   - Region intersection: `STATISTICAL_OPERATIONS ∩ AGGREGATION`
   - Functional mapping: `REDUCE(MEAN)`

2. **"mean" in sentiment context**:
   - Linguistic embedding activates regions near: [negative, hostile, unkind]
   - Contextual words "filter" and "comments" reinforce sentiment interpretation
   - Region intersection: `SENTIMENT_ANALYSIS ∩ FILTERING`
   - Functional mapping: `FILTER(SENTIMENT_NEGATIVE)`

**Resolution Process**:
```python
def resolve_mean(context_ast):
    mean_embedding = embed("mean")
    context_embeddings = [embed(node) for node in context_ast.neighbors]
    
    # Calculate region activation strengths
    statistical_activation = cosine_similarity(
        mean_embedding,
        average(context_embeddings, statistical_region)
    )
    sentiment_activation = cosine_similarity(
        mean_embedding,
        average(context_embeddings, sentiment_region)
    )
    
    if statistical_activation > sentiment_activation + threshold:
        return REDUCE_MEAN
    elif sentiment_activation > statistical_activation + threshold:
        return FILTER_NEGATIVE
    else:
        return REQUEST_CLARIFICATION
```

#### 4.3 Example 2: Semantic Ambiguity - "Important Clients"

**Input**: "Show me the important clients"

**Region Analysis**:

The term "important" has no direct functional primitive but overlaps with multiple concrete concepts:

1. **Revenue-based importance**:
   - Region overlap: `HIGH_VALUE ∩ CUSTOMER`
   - Functional interpretation: `FILTER(clients, GREATER_THAN(GET_FIELD('revenue'), PERCENTILE(revenues, 90)))`

2. **Interaction-based importance**:
   - Region overlap: `FREQUENT_INTERACTION ∩ CUSTOMER`
   - Functional interpretation: `FILTER(clients, GREATER_THAN(GET_FIELD('interaction_count'), THRESHOLD))`

3. **Strategic importance**:
   - Region overlap: `STRATEGIC_PARTNER ∩ CUSTOMER`
   - Functional interpretation: `FILTER(clients, EQUALS(GET_FIELD('partnership_tier'), 'strategic'))`

**Multi-Criteria Resolution**:
```python
def resolve_important(entity_type, available_fields):
    importance_regions = []
    
    # Check which "importance" criteria have corresponding fields
    if 'revenue' in available_fields:
        importance_regions.append({
            'region': 'high_revenue',
            'weight': 0.4,
            'operation': FILTER_HIGH_REVENUE
        })
    
    if 'interaction_count' in available_fields:
        importance_regions.append({
            'region': 'frequent_interaction',
            'weight': 0.3,
            'operation': FILTER_FREQUENT
        })
    
    if 'partnership_tier' in available_fields:
        importance_regions.append({
            'region': 'strategic_value',
            'weight': 0.3,
            'operation': FILTER_STRATEGIC
        })
    
    # Combine criteria with weights
    return COMPOSE_WITH_WEIGHTS(importance_regions)
```

#### 4.4 Interactive Clarification Strategies

When region overlap is too ambiguous, the system generates clarifying questions:

```python
def generate_clarification(ambiguous_term, candidate_regions):
    question = f"When you say '{ambiguous_term}', do you mean:"
    
    for i, region in enumerate(candidate_regions):
        example = generate_example(region)
        question += f"\n{i+1}. {region.description} (e.g., {example})"
    
    return question
```

**Example Output**:
"When you say 'important clients', do you mean:
1. High-revenue clients (e.g., clients with >$1M annual revenue)
2. Frequently active clients (e.g., clients with >50 transactions/month)
3. Strategic partner clients (e.g., clients marked as 'strategic' tier)"

### 5. Evaluation Framework

#### 5.1 Traditional Metrics

1. **Functional Accuracy**: Percentage of inputs correctly mapped to target functional AST
2. **Execution Accuracy**: Percentage of generated programs that produce correct output
3. **Parse Success Rate**: Percentage of inputs successfully parsed into Linguistic AST

#### 5.2 Novel Metric 1: Semantic Equivalence Score (SES)

**Definition**: Measures whether the generated Functional AST produces semantically equivalent results to the target, even with different implementation.

**Calculation**:
```python
def semantic_equivalence_score(generated_ast, target_ast, test_inputs):
    score = 0
    for test_input in test_inputs:
        generated_output = execute(generated_ast, test_input)
        target_output = execute(target_ast, test_input)
        
        if outputs_equivalent(generated_output, target_output):
            score += 1
        elif outputs_partially_equivalent(generated_output, target_output):
            score += partial_credit(generated_output, target_output)
    
    return score / len(test_inputs)
```

**Example**:
- Target: `COMPOSE(FILTER(age > 30), MAP(GET_NAME))`
- Generated: `COMPOSE(MAP(GET_NAME), FILTER(age > 30))`
- If both produce same final output set: SES = 1.0

**Value**: Recognizes functionally correct alternative implementations

#### 5.3 Novel Metric 2: Compositional Correctness Score (CCS)

**Definition**: Evaluates how well the generated program's structure aligns with the logical structure implied by the Linguistic AST.

**Components**:
1. **Structural Alignment** (40%): Does the functional AST mirror the linguistic AST's hierarchy?
2. **Operation Ordering** (30%): Are operations sequenced as implied by the language?
3. **Semantic Preservation** (30%): Are all linguistic concepts represented functionally?

**Calculation**:
```python
def compositional_correctness_score(linguistic_ast, functional_ast):
    structural_score = tree_similarity(
        linguistic_ast.structure,
        functional_ast.structure
    )
    
    ordering_score = sequence_alignment(
        linguistic_ast.operation_sequence,
        functional_ast.operation_sequence
    )
    
    semantic_score = concept_coverage(
        linguistic_ast.semantic_nodes,
        functional_ast.primitive_nodes
    )
    
    return (0.4 * structural_score + 
            0.3 * ordering_score + 
            0.3 * semantic_score)
```

**Value**: Ensures the system learns proper compositional reasoning, not just input-output mappings

#### 5.4 Novel Metric 3: Ambiguity Resolution Confidence (ARC)

**Definition**: Measures how confidently the system resolves ambiguous inputs without requiring clarification.

**Calculation**:
```python
def ambiguity_resolution_confidence(input, resolution):
    all_interpretations = generate_all_interpretations(input)
    chosen_interpretation = resolution
    
    if len(all_interpretations) == 1:
        return 1.0  # No ambiguity
    
    chosen_score = region_activation_score(chosen_interpretation)
    other_scores = [region_activation_score(i) for i in all_interpretations 
                    if i != chosen_interpretation]
    
    # High confidence if chosen score significantly higher
    separation = chosen_score - max(other_scores)
    return sigmoid(separation / temperature)
```

**Value**: Tracks improvement in handling ambiguous language over time

#### 5.5 Holistic Evaluation Protocol

**Test Set Design**:
1. **Canonical Set**: Standard, unambiguous examples (40%)
2. **Ambiguous Set**: Multiple valid interpretations (30%)
3. **Compositional Set**: Complex multi-step operations (20%)
4. **Adversarial Set**: Edge cases and unusual phrasings (10%)

**Success Criteria by Stage**:
- Stage 1: SES ≥ 0.95, CCS ≥ 0.90, ARC ≥ 0.85
- Stage 2: SES ≥ 0.90, CCS ≥ 0.85, ARC ≥ 0.80
- Stage 3: SES ≥ 0.85, CCS ≥ 0.80, ARC ≥ 0.75
- Stage 4: SES ≥ 0.80, CCS ≥ 0.75, ARC ≥ 0.70
- Stage 5: SES ≥ 0.75, CCS ≥ 0.70, ARC ≥ 0.65

### 6. Conclusion and Future Vision

The Language Bridge represents a fundamental shift in how computational systems understand human intent. By creating a principled mapping between the compositional structure of natural language and the discovered primitives of RegionAI, we enable true semantic understanding rather than pattern matching.

The progressive curriculum, sophisticated ambiguity resolution, and comprehensive evaluation framework ensure that the system learns robust, generalizable mappings. Starting with data processing specifications provides immediate value while building toward the ultimate goal: a system that can understand any computational request expressed in natural language and implement it correctly.

This architecture lays the foundation for RegionAI to become not just a tool, but a true collaborator in the creative process of software development. As the system masters increasingly complex linguistic patterns, it will unlock new possibilities for human-computer collaboration that we can barely imagine today.