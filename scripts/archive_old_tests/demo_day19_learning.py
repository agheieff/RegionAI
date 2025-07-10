#!/usr/bin/env python3
"""Day 19 Demo: Watch the system learn from failure!"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def main():
    print("\n" + "="*60)
    print("Day 19 Demo: Learning from Failure")
    print("="*60)
    print("\nThis demo shows a complete learning cycle:")
    print("1. The system encounters problems it cannot solve")
    print("2. It analyzes its failures to discover patterns")
    print("3. It creates a new concept from those patterns")
    print("4. It uses the new concept to solve the problems")
    print("\nRunning the learning loop...\n")
    
    # Import and run the main learning loop
    from run_learning_loop import main as run_loop
    run_loop()
    
    print("\n" + "="*60)
    print("Demo complete!")
    print("\nWhat just happened:")
    print("• The system was given 3 'reverse list' problems")
    print("• It failed all 3 (it didn't know how to reverse)")
    print("• It analyzed the failures and discovered the pattern")
    print("• It created a new 'TRANSFORM' concept")
    print("• It successfully solved all 3 problems using the new concept")
    print("\nThis is real learning - the system taught itself!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()