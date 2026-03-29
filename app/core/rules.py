from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class RuleViolation:
    rule_name: str
    description: str
    severity: str
    suggestion: str


def count_question_marks(text: str) -> int:
    return text.count("?")


def has_diagnosis_claim(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "he has ptsd",
        "she has ptsd",
        "this is definitely ptsd",
        "he is dissociating",
        "she is dissociating",
    ]
    return any(pattern in lowered for pattern in patterns)


def has_confrontational_language(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "make him explain",
        "make her explain",
        "confront him",
        "confront her",
        "push him",
        "push her",
        "force him",
        "force her",
    ]
    return any(pattern in lowered for pattern in patterns)


def is_concise(text: str, max_words: int = 90) -> bool:
    return len(re.findall(r"\b\w+\b", text)) <= max_words
