#!/usr/bin/env python3
"""
Moltbook Verification Challenge Solver
Extracts numbers from obfuscated math word problems and computes the answer.
Handles addition, subtraction, multiplication, division.
Usage:
    python3 solve_verification.py "challenge text here"
    echo "challenge text" | python3 solve_verification.py
"""

import re
import sys
from typing import List

# Word-to-number mapping for written-out numbers
WRITTEN_NUMBERS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000
}

# Operation keywords
OPERATIONS = {
    'plus': '+', 'add': '+', 'sum': '+', 'total': '+', 'and': '+',
    'minus': '-', 'subtract': '-', 'difference': '-',
    'times': '*', 'multiplied': '*', 'multiply': '*', 'product': '*', 'by': '*',
    'divided': '/', 'divide': '/', 'quotient': '/', 'over': '/',
}

def extract_numbers(text: str) -> List[float]:
    """Extract all numbers (digits and written words) from text."""
    numbers = []
    text_lower = text.lower()
    
    # First pass: find digit numbers
    digit_matches = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    for match in digit_matches:
        numbers.append(float(match))
    
    # Second pass: find written numbers
    # Clean text for word matching
    clean_text = re.sub(r'[^a-z\s]', ' ', text_lower)
    words = clean_text.split()
    
    for word in words:
        if word in WRITTEN_NUMBERS:
            numbers.append(float(WRITTEN_NUMBERS[word]))
    
    return numbers

def detect_operation(text: str) -> str:
    """Detect math operation from text."""
    text_lower = text.lower()
    for op_word, op_symbol in OPERATIONS.items():
        if op_word in text_lower:
            return op_symbol
    # Default to addition if no operation detected
    return '+'

def solve_challenge(text: str) -> str:
    """
    Solve a Moltbook verification challenge.
    Returns answer formatted as 'XX.00'.
    """
    numbers = extract_numbers(text)
    operation = detect_operation(text)
    
    if not numbers:
        # Fallback: try to find any digit sequence
        fallback = re.findall(r'\d+', text)
        if fallback:
            numbers = [float(n) for n in fallback]
        else:
            raise ValueError(f"Could not extract numbers from: {text[:100]}...")
    
    if len(numbers) == 1:
        result = numbers[0]
    elif len(numbers) == 2:
        if operation == '+':
            result = numbers[0] + numbers[1]
        elif operation == '-':
            result = numbers[0] - numbers[1]
        elif operation == '*':
            result = numbers[0] * numbers[1]
        elif operation == '/':
            result = numbers[0] / numbers[1] if numbers[1] != 0 else numbers[0]
        else:
            result = sum(numbers)
    else:
        # Multiple numbers: sum them
        result = sum(numbers)
    
    return f"{result:.2f}"

def main():
    # Read challenge from argument or stdin
    if len(sys.argv) > 1:
        challenge = ' '.join(sys.argv[1:])
    else:
        challenge = sys.stdin.read().strip()
    
    if not challenge:
        print("Usage: python3 solve_verification.py \"challenge text\"", file=sys.stderr)
        print("   or: echo \"challenge text\" | python3 solve_verification.py", file=sys.stderr)
        sys.exit(1)
    
    try:
        answer = solve_challenge(challenge)
        print(answer)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()