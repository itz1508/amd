"""
Difficulty Gate Module

Distinguishes easy tasks (solve locally, skip subagent) from hard tasks
(solve via local model + subagent verification, then Fireworks rescue).

Easy tasks are characterized by:
- Simple arithmetic
- Clear sentiment classification
- Basic NER
- Basic yes/no logic
- Clear one-sentence summary requirements

Hard tasks are characterized by:
- Code generation/debugging
- Multi-step logic
- Ambiguous constraints
- Long prompts
- Strict formatting requirements
- Validator cannot prove answer
- Low confidence classification
"""

import re
from typing import Any, Dict, List, Tuple


# EASY TASK PATTERNS - These can be solved deterministically or without subagent review
EASY_PATTERNS = {
    'mathematical_reasoning': [
        r'what\s+is\s+[\d\s+\-*/().]+\??',
        r'calculate\s+[\d\s+\-*/().]+',
        r'compute\s+[\d\s+\-*/().]+',
        r'solve\s+\d+\s*[+*/\-]\s*\d+\s*[=]',
        r'^[\s\d+\-*/().]+$',  # Just math expressions
    ],
    'sentiment_classification': [
        r'classify\s+(this\s+)?(review|text)\s+as\s+(positive|negative|neutral)',
        r'sentiment\s+of\s+["\']',  # Quote follows
        r'is\s+(this|the)\s+(positive|negative)\??',
    ],
    'named_entity_recognition': [
        r'extract\s+(the\s+)?entities\s+from\s+["\']',  # Just extract
        r'named\s+entities\s+in\s+["\']',
    ],
    'text_summarisation': [
        r'summarize\s+(in\s+\d+\s+words)\s+["\']',  # Word limit + quoted text
        r'summarize\s+(in\s+\d+\s+sentences)\s+["\']',  # Sentence limit
        r'one\s+sentence\s+summary',
    ],
    'logical_reasoning': [
        r'(a\s+or\s+b\??)\s*$',  # Simple A/B choice
        r'(yes|no)\s+or\s+(no|yes)\??',  # Simple yes/no
    ],
    'code_generation': [
        r'(write|generate)\s+(a\s+)?(simple\s+)?(function|method)\s+(to|that)',  # Simple function
        r'return\s+["\'][a-z]+["\']\s*$',  # Simple return string
    ],
    'code_debugging': [
        r'fix\s+this\s+(simple\s+)?bug',
        r'error\s+on\s+line\s+\d+',
    ],
    'factual_knowledge': [
        r'what\s+is\s+(the\s+)?[a-z]+\s*\?*$',  # Direct "what is X" question
        r'who\s+(is|was)\s+["\']',  # Who is...
        r'when\s+(did|was)\s+["\']',  # When...
    ],
}


# HARD INDICATORS - These suggest task needs subagent/verification
HARD_INDICATORS = [
    r'complex',
    r'multiple\s+step',
    r'multiple\s+constraint',
    r'must\s+(also|additionally)',
    r'and\s+output\s+(json|yaml|xml)',
    r'while\s+ensuring',
    r'without\s+violating',
    r'under\s+\d+\s+(byte|char)',
    r'(at\s+least|at\s+most)\s+\d+',
    r'find\s+all',
    r'list\s+all',
    r'enumerate',
    r'generate\s+.*test',
    r'write\s+comprehensive',
    r'implement\s+.*algorithm',
    r'optimize',
    r'refactor',
    r'hackathon',
    r'competitive',
    r'efficient',
    r'correct',
    r'buggy',
    r'debug',
    r'fix\s+.*error',
    r'why\s+does',
    r'how\s+to\s+fix',
]


def assess_difficulty(category: str, prompt: str) -> Tuple[bool, str]:
    """
    Assess whether a task is easy or hard.
    
    Args:
        category: The task category
        prompt: The task prompt
        
    Returns:
        Tuple of (is_easy, reason)
    """
    prompt_lower = prompt.lower().strip()
    
    # Check for hard indicators first
    for pattern in HARD_INDICATORS:
        if re.search(pattern, prompt_lower):
            return False, f"Hard indicator found: {pattern}"
    
    # Check for easy patterns matching category
    category_patterns = EASY_PATTERNS.get(category, [])
    for pattern in category_patterns:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True, f"Easy pattern match: {pattern}"
    
    # Length heuristic - long prompts are harder
    if len(prompt) > 500:
        return False, "Long prompt (>500 chars) suggests complex reasoning"
    
    # Multiple constraints heuristic
    if len(re.findall(r'(must|should|require)', prompt_lower)) > 2:
        return False, "Multiple constraints detected"
    
    # Default: medium difficulty - use local model but allow verifier
    # This is conservative - better to verify than to miss
    if category in ['code_generation', 'code_debugging', 'logical_reasoning']:
        return False, "Category requires verification by default"
    
    # Easy by default for simple categories
    if category in ['mathematical_reasoning', 'sentiment_classification']:
        return True, "Simple category by default"
    
    return False, "Uncertain - route with verification"


def should_skip_subagent(category: str, prompt: str, validation_passed: bool) -> Tuple[bool, str]:
    """
    Determine if we should skip subagent for a task.
    
    Subagent is skipped when:
    1. Task is easy AND
    2. Local validation passed OR task doesn't require verification
    
    Args:
        category: The task category
        prompt: The task prompt
        validation_passed: Whether local validation passed
        
    Returns:
        Tuple of (should_skip, reason)
    """
    is_easy, reason = assess_difficulty(category, prompt)
    
    if is_easy and validation_passed:
        return True, reason
    
    return False, reason


def get_category_easiness_score(category: str, prompt: str) -> float:
    """
    Return a score from 0.0 (very hard) to 1.0 (very easy).
    
    This can be used for routing decisions when deterministic tools
    can't fully solve.
    """
    is_easy, _ = assess_difficulty(category, prompt)
    
    # Base scores per category
    base_scores = {
        'mathematical_reasoning': 0.95,  # Usually easy
        'sentiment_classification': 0.90,  # Usually easy
        'text_summarisation': 0.70,  # Sometimes easy
        'named_entity_recognition': 0.75,  # Usually easy
        'factual_knowledge': 0.60,  # Mixed
        'logical_reasoning': 0.40,  # Often needs reasoning
        'code_generation': 0.20,  # Usually hard
        'code_debugging': 0.30,  # Usually hard
    }
    
    score = base_scores.get(category, 0.5)
    
    # Adjust based on prompt patterns
    if is_easy:
        score = min(0.95, score + 0.1)
    else:
        score = max(0.1, score - 0.1)
    
    return round(score, 2)


# Singleton
_gate_instance = None


def get_difficulty_gate():
    """Get the difficulty gate instance."""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = {
            'assess_difficulty': assess_difficulty,
            'should_skip_subagent': should_skip_subagent,
            'get_category_easiness_score': get_category_easiness_score,
        }
    return _gate_instance