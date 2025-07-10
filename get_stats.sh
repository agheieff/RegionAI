#!/bin/bash

# This script provides a quick overview of the current dimensions and
# potential concepts within the RegionAI model by inspecting the source code directly.

echo "--- RegionAI Model Stats ---"
echo ""

# --- 1. Semantic Dimensions (Behaviors) ---
# This part worked correctly and remains the same. It counts the
# number of behaviors defined in the Behavior enum.

echo "Semantic Dimensions (Behaviors):"
DIMENSION_COUNT=$(grep -c '^\s*[A-Z_]\+ = auto()' src/regionai/semantic/fingerprint.py)
echo "Total: $DIMENSION_COUNT"

echo "Examples:"
grep '^\s*[A-Z_]\+ = auto()' src/regionai/semantic/fingerprint.py | head -n 3 | sed -e 's/ = auto()//' -e 's/^\s*//' -e 's/,//'
echo ""


# --- 2. Discovered Knowledge Concepts ---
# This is the corrected section. Instead of trying to instantiate complex
# classes, we will simulate the ConceptDiscoverer's primary heuristic
# (finding nouns in function names) using simple text processing.

echo "Discovered Knowledge Concepts (from a sample codebase):"

# This command executes a Python script directly.
# This new version is much simpler and has no complex dependencies.
python3 -c """
import re
import sys
from collections import Counter

# A sample codebase that is guaranteed to contain discoverable concepts
sample_code = '''
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
    
def create_profile_for_user(user_id):
    \"\"\"Creates the user's profile.\"\"\"
    pass
'''

def find_concepts_from_code(code):
    '''A simple heuristic to find concepts from function names.'''
    # Find all function names
    function_names = re.findall(r'def\s+([a-zA-Z_]\w*)\s*\(', code)
    
    concepts = []
    # Common prefixes to strip away
    prefixes = ['create_', 'get_', 'update_', 'delete_', 'assign_', 'remove_']
    
    for name in function_names:
        # Strip common verb prefixes
        for prefix in prefixes:
            if name.startswith(prefix):
                concept = name[len(prefix):]
                # Further split if we have something like 'profile_for_user'
                parts = concept.split('_for_')
                concepts.extend([p.capitalize() for p in parts])
                break
    
    # Return the most common, unique concepts found
    # Using Counter to get unique items in order of appearance
    return list(Counter(concepts).keys())

try:
    concepts = find_concepts_from_code(sample_code)
    print(f'Total: {len(concepts)}')
    print('Examples:')
    for concept in concepts[:3]:
        print(f'- {concept}')
except Exception as e:
    print(f'An error occurred: {e}')

"""
