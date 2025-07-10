#!/bin/bash

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}--- 1. Verifying Project File Structure ---${NC}"
ls -R src/regionai/
echo ""

echo -e "${YELLOW}--- 2. Checking Dependencies in pyproject.toml ---${NC}"
cat pyproject.toml
echo ""

echo -e "${YELLOW}--- 3. Inspecting Knowledge Graph Implementation (Belief Tracking) ---${NC}"
echo "File: src/regionai/knowledge/graph.py"
echo "--------------------------------------------------"
cat src/regionai/knowledge/graph.py
echo ""

echo -e "${YELLOW}--- 4. Inspecting Knowledge Linker Implementation ---${NC}"
echo "File: src/regionai/knowledge/linker.py"
echo "--------------------------------------------------"
cat src/regionai/knowledge/linker.py
echo ""

echo -e "${YELLOW}--- 5. Verifying Pipeline Integration ---${NC}"
echo "File: src/regionai/pipeline/api.py"
echo "--------------------------------------------------"
# Using grep to find the relevant function and its surroundings
grep -C 10 "build_knowledge_graph_from_codebase" src/regionai/pipeline/api.py || echo "Function not found or file does not exist."
echo ""

echo -e "${YELLOW}--- 6. Running Full Test Suite ---${NC}"
echo "This is the definitive check. All tests must pass."
# Assuming pytest is the test runner
if command -v pytest &> /dev/null
then
    pytest
else
    echo "pytest command not found. Please install it to run the tests."
fi

echo -e "${GREEN}--- Verification Script Finished ---${NC}"
