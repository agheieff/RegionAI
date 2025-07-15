"""
Tests for the Lean parser.
"""

import pytest
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pathlib import Path
import tempfile

from tier2.linguistics.lean_parser import (
    LeanParser, LeanFileValidator
)


class TestLeanParser:
    """Test the LeanParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LeanParser()
    
    def test_parse_simple_theorem(self):
        """Test parsing a simple theorem without parameters."""
        content = "theorem identity : p → p"
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        theorem = theorems[0]
        assert theorem.name == "identity"
        assert theorem.statement == "p → p"
        assert len(theorem.hypotheses) == 0
    
    def test_parse_theorem_with_single_param(self):
        """Test parsing theorem with single parameter."""
        content = "theorem self_impl (p : Prop) : p → p"
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        theorem = theorems[0]
        assert theorem.name == "self_impl"
        assert theorem.statement == "p → p"
        assert len(theorem.hypotheses) == 1
        assert theorem.hypotheses[0].name == "p"
        assert theorem.hypotheses[0].type_expr == "Prop"
    
    def test_parse_theorem_with_multiple_params(self):
        """Test parsing theorem with multiple parameters."""
        content = "theorem modus_ponens (p : Prop) (q : Prop) : p → (p → q) → q"
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        theorem = theorems[0]
        assert len(theorem.hypotheses) == 2
        assert theorem.hypotheses[0].name == "p"
        assert theorem.hypotheses[0].type_expr == "Prop"
        assert theorem.hypotheses[1].name == "q"
        assert theorem.hypotheses[1].type_expr == "Prop"
    
    def test_parse_theorem_with_shared_type(self):
        """Test parsing theorem where multiple params share a type."""
        content = "theorem and_comm (p q : Prop) : p ∧ q → q ∧ p"
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        theorem = theorems[0]
        assert len(theorem.hypotheses) == 2
        assert theorem.hypotheses[0].name == "p"
        assert theorem.hypotheses[0].type_expr == "Prop"
        assert theorem.hypotheses[1].name == "q"
        assert theorem.hypotheses[1].type_expr == "Prop"
    
    def test_parse_multiple_theorems(self):
        """Test parsing multiple theorems from content."""
        content = """
        theorem theorem1 : p → p
        theorem theorem2 (p : Prop) : p → p
        theorem theorem3 (p q : Prop) : p → q → p
        """
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 3
        assert theorems[0].name == "theorem1"
        assert theorems[1].name == "theorem2"
        assert theorems[2].name == "theorem3"
    
    def test_parse_with_comments(self):
        """Test parsing with comments."""
        content = """
        -- This is a comment
        theorem with_comment : p → p
        
        theorem another -- inline comment
            : q → q
        """
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 2
        assert theorems[0].name == "with_comment"
        assert theorems[1].name == "another"
    
    def test_parse_multiline_theorem(self):
        """Test parsing theorem spanning multiple lines."""
        content = """
        theorem multiline
            (p : Prop)
            (q : Prop)
            : p → q → p ∧ q
        """
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        theorem = theorems[0]
        assert theorem.name == "multiline"
        assert len(theorem.hypotheses) == 2
        assert theorem.statement == "p → q → p ∧ q"
    
    def test_parse_complex_types(self):
        """Test parsing with complex type expressions."""
        content = "theorem complex_type (f : Nat → Nat) (x : Nat) : f x = f x"
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 1
        assert len(theorems[0].hypotheses) == 2
        assert theorems[0].hypotheses[0].name == "f"
        assert theorems[0].hypotheses[0].type_expr == "Nat → Nat"
        assert theorems[0].hypotheses[1].name == "x"
        assert theorems[0].hypotheses[1].type_expr == "Nat"
    
    def test_parse_unicode_operators(self):
        """Test parsing with Unicode logical operators."""
        content = """
        theorem unicode1 : p ∧ q → p
        theorem unicode2 : p ∨ q → r
        theorem unicode3 : ¬p → ¬¬¬p
        theorem unicode4 : p ↔ q
        """
        theorems = self.parser.parse_content(content)
        
        assert len(theorems) == 4
        assert "∧" in theorems[0].statement
        assert "∨" in theorems[1].statement
        assert "¬" in theorems[2].statement
        assert "↔" in theorems[3].statement
    
    def test_parse_file(self):
        """Test parsing from a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
            f.write("theorem from_file (p : Prop) : p → p")
            temp_path = Path(f.name)
        
        try:
            theorems = self.parser.parse_file(temp_path)
            assert len(theorems) == 1
            assert theorems[0].name == "from_file"
            assert theorems[0].metadata['source_file'] == str(temp_path)
        finally:
            temp_path.unlink()
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file(Path("nonexistent.lean"))
    
    def test_parse_empty_content(self):
        """Test parsing empty content."""
        theorems = self.parser.parse_content("")
        assert len(theorems) == 0
    
    def test_parse_no_theorems(self):
        """Test parsing content with no theorems."""
        content = """
        -- Just comments
        -- No theorems here
        """
        theorems = self.parser.parse_content(content)
        assert len(theorems) == 0
    
    def test_parse_tactic_line(self):
        """Test parsing individual tactic lines."""
        test_cases = [
            ("intro h", "intro", ["h"]),
            ("apply lemma", "apply", ["lemma"]),
            ("exact proof", "exact", ["proof"]),
            ("simp", "simp", []),
            ("rewrite h1 at h2", "rewrite", ["h1", "at", "h2"]),
        ]
        
        for line, expected_type, expected_args in test_cases:
            tactic = self.parser._parse_tactic_line(line)
            assert tactic is not None
            assert tactic.tactic_type.value == expected_type
            assert tactic.arguments == expected_args
    
    def test_parse_proof(self):
        """Test parsing a proof."""
        proof_str = """by
        intro h
        apply modus_ponens
        exact h
        """
        
        tactics = self.parser.parse_proof(proof_str)
        assert len(tactics) == 3
        assert tactics[0].tactic_type.value == "intro"
        assert tactics[1].tactic_type.value == "apply"
        assert tactics[2].tactic_type.value == "exact"


class TestLeanFileValidator:
    """Test the LeanFileValidator class."""
    
    def test_validate_valid_file(self):
        """Test validating a well-formed file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
            f.write("""
            theorem test1 : p → p
            theorem test2 (p : Prop) : p → p
            """)
            temp_path = Path(f.name)
        
        try:
            is_valid, issues = LeanFileValidator.validate_file(temp_path)
            assert is_valid
            assert len(issues) == 0
        finally:
            temp_path.unlink()
    
    def test_validate_unbalanced_parens(self):
        """Test detecting unbalanced parentheses."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
            f.write("theorem bad (p : Prop : p → p")
            temp_path = Path(f.name)
        
        try:
            is_valid, issues = LeanFileValidator.validate_file(temp_path)
            assert not is_valid
            assert any("Unbalanced" in issue for issue in issues)
        finally:
            temp_path.unlink()
    
    def test_validate_no_theorems(self):
        """Test detecting files with no theorems."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
            f.write("-- Just a comment")
            temp_path = Path(f.name)
        
        try:
            is_valid, issues = LeanFileValidator.validate_file(temp_path)
            assert not is_valid
            assert any("No theorem" in issue for issue in issues)
        finally:
            temp_path.unlink()
    
    def test_validate_missing_colon(self):
        """Test detecting missing colon in theorem."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
            f.write("theorem missing_colon p → p")
            temp_path = Path(f.name)
        
        try:
            is_valid, issues = LeanFileValidator.validate_file(temp_path)
            assert not is_valid
            assert any("missing colon" in issue for issue in issues)
        finally:
            temp_path.unlink()
    
    def test_check_balanced_parens(self):
        """Test the balanced parentheses checker."""
        assert LeanFileValidator._check_balanced_parens("()")
        assert LeanFileValidator._check_balanced_parens("(())")
        assert LeanFileValidator._check_balanced_parens("{[()]}")
        assert not LeanFileValidator._check_balanced_parens("(")
        assert not LeanFileValidator._check_balanced_parens(")")
        assert not LeanFileValidator._check_balanced_parens("([)]")