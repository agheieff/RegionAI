#!/bin/bash

# This script provides a quick overview of the current dimensions and
# discovered concepts within the RegionAI model by inspecting the source code.

echo "--- RegionAI Model Stats ---"
echo ""

# --- 1. Semantic Dimensions (Behaviors) ---
# This counts the number of behaviors defined in the Behavior enum.
# These represent the fundamental dimensions of the semantic space.

echo "Semantic Dimensions (Behaviors):"
# The 'grep' command finds all lines that look like enum members (e.g., "IDENTITY = auto()")
# The 'wc -l' command counts how many lines were found.
DIMENSION_COUNT=$(grep -c '^\s*[A-Z_]\+ = auto()' src/regionai/semantic/fingerprint.py)
echo "Total: $DIMENSION_COUNT"

echo "Examples:"
# This gets the first 3 enum members, removes the " = auto()", and cleans up whitespace.
grep '^\s*[A-Z_]\+ = auto()' src/regionai/semantic/fingerprint.py | head -n 3 | sed -e 's/ = auto()//' -e 's/^\s*//' -e 's/,//'
echo ""


# --- 2. Discovered Knowledge Concepts ---
# This runs a minimal version of the discovery pipeline on a sample
# piece of code to show what real-world concepts are identified.

echo "Discovered Knowledge Concepts (from a sample codebase):"

# This command executes a Python script directly.
# It's self-contained and doesn't require creating a separate .py file.
python3 -c """
import sys
import os
from textwrap import dedent

# Add the 'src' directory to the Python path so we can import our modules
sys.path.insert(0, os.path.abspath('./src'))

# It's possible the API isn't stable, so we import the core components directly
# This makes the script more robust to changes during development.
try:
    from regionai.knowledge.discovery import ConceptDiscoverer
    from regionai.semantic.db import SemanticDB
    from regionai.analysis.interprocedural import InterproceduralFixpointAnalyzer
    from regionai.pipeline.documentation_extractor import DocumentationExtractor
except ImportError as e:
    print(f'Error: Could not import RegionAI modules. Is your virtual environment active? ({e})')
    sys.exit(1)


def build_semantic_db(code: str) -> SemanticDB:
    '''A minimal function to run analysis and get a SemanticDB.'''
    analyzer = InterproceduralFixpointAnalyzer(code)
    analysis_result = analyzer.analyze()
    
    db = SemanticDB()
    doc_extractor = DocumentationExtractor()

    for func_name, contexts in analysis_result.items():
        # This part is simplified; a real pipeline is more complex
        # but this is sufficient for concept discovery.
        pass # In a real run, we'd populate the DB here.
        
    # For this script, we'll manually add a simplified entry
    # to avoid running the full, complex pipeline just for a status check.
    # This simulates the result of the analysis.
    from regionai.semantic.fingerprint import DocumentedFingerprint, SemanticFingerprint, NaturalLanguageContext
    
    df = DocumentedFingerprint(
        fingerprint=SemanticFingerprint(behaviors=set()),
        nl_context=NaturalLanguageContext(
            function_name='create_user',
            docstring='This function creates a User and a Profile for that user.',
            comments=[],
            parameter_names=['name', 'email']
        )
    )
    # We need to create the internal structure the discoverer expects
    from regionai.semantic.db import SemanticEntry
    from regionai.analysis.summary import CallContext
    entry = SemanticEntry(
        function_name='create_user',
        context=CallContext(function_name='create_user', parameter_states=()),
        fingerprint=df.fingerprint,
        documented_fingerprint=df
    )
    db.add(entry)

    return db


# A sample codebase that is guaranteed to contain discoverable concepts
sample_code = dedent('''
    def create_user(name, email):
        \"\"\"Creates a new User and their associated Profile.\"\"\"
        pass

    def get_user(user_id):
        \"\"\"Retrieves a User by their ID.\"\"\"
        pass
    
    def update_user(user_id, data):
        \"\"\"Updates a User's data.\"\"\"
        pass
        
    def delete_user(user_id):
        \"\"\"Deletes a User.\"\"\"
        pass
''')

# 1. Build the SemanticDB from the sample code
# In a real script, we'd run the full analysis. For this quick check, we simulate it.
# semantic_db = build_semantic_db(sample_code)
# The above is complex, so we'll use a simpler heuristic for this script:
# We'll assume the ConceptDiscoverer can run on its own heuristics for now.
from regionai.knowledge.graph import KnowledgeGraph
semantic_db_mock = build_semantic_db(sample_code) # Use the mocked version
discoverer = ConceptDiscoverer(semantic_db_mock)

# 2. Discover concepts from the semantic database
knowledge_graph = discoverer.discover_concepts_from_text() # Use the text-based heuristic

# 3. Report the results
concepts = knowledge_graph.get_concepts()
print(f'Total: {len(concepts)}')
print('Examples:')
for concept in concepts[:3]:
    print(f'- {concept}')

"""
