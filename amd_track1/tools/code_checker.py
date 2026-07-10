import ast
import json
import re
from typing import Optional, Tuple


class CodeSyntaxChecker:
    """Code syntax validator."""
    
    SUPPORTED_LANGUAGES = ["python", "json", "javascript", "typescript"]
    
    def detect_language(self, code: str) -> str:
        """Detect the programming language of code."""
        code_lower = code.lower()
        
        if re.search(r'def \w+\s*\(', code) or re.search(r'class \w+', code):
            return 'python'
        
        stripped = code.strip()
        if (stripped.startswith('{') and stripped.endswith('}')) or            (stripped.startswith('[') and stripped.endswith(']')):
            return 'json'
        
        if re.search(r'function\s+\w+\s*\(', code):
            return 'javascript'
        
        return 'python'
    
    def check_python_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check Python code syntax using ast.parse."""
        try:
            ast.parse(code)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def check_json_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check JSON syntax."""
        try:
            json.loads(code)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def check_syntax(self, code: str, language: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Check code syntax for the detected or specified language."""
        if not code.strip():
            return False, "Empty code"
        
        if language is None:
            language = self.detect_language(code)
        
        language = language.lower()
        
        if language == 'python':
            return self.check_python_syntax(code)
        elif language == 'json':
            return self.check_json_syntax(code)
        elif language in ['javascript', 'typescript', 'js', 'ts']:
            return True, None  # Skip detailed JS validation for now
        else:
            return self.check_python_syntax(code)
    
    def extract_code_from_text(self, text: str) -> list:
        """Extract code blocks from text."""
        # Look for markdown code fences
        pattern = re.compile(r'```(?:\w+)?\n([\s\S]*?)```')
        matches = pattern.findall(text)
        
        codes = []
        for match in matches:
            stripped = match.strip()
            if stripped:
                codes.append(stripped)
        
        if not codes:
            # If no fences, return the whole text as a single code block
            # (the syntax checker will handle validation)
            codes = [text]
        
        return codes
    
    def validate_code_output(self, output: str, 
                              expected_language: Optional[str] = None,
                              has_signature: bool = False,
                              signature: Optional[str] = None) -> Tuple[bool, list]:
        """Validate code generation output."""
        errors = []
        codes = self.extract_code_from_text(output)
        if not codes:
            errors.append("No code found in output")
            return False, errors
        for i, code in enumerate(codes):
            lang = expected_language or self.detect_language(code)
            valid, error = self.check_syntax(code, lang)
            if not valid:
                errors.append(f"Code block {i+1} syntax error: {error}")
        if has_signature and signature:
            if signature not in output:
                errors.append(f"Expected signature not found")
        return len(errors) == 0, errors
    
    def check_function_signature(self, code: str, expected_signature: str) -> bool:
        """Check if code contains the expected function signature."""
        normalized_code = ' '.join(code.split())
        normalized_sig = ' '.join(expected_signature.split())
        return normalized_sig in normalized_code


code_checker = CodeSyntaxChecker()
