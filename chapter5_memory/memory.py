"""
Chapter 5 — a minimal long-term memory store.

Deliberately simple: a JSON file on disk + naive keyword-overlap
retrieval. This is enough to demonstrate the *concept* of long-term
memory (persistence + retrieval) without requiring an embeddings model
or a vector database. Swap `retrieve()` for a real vector search later
without touching anything else in this file's interface.
"""
import json
import os
import re
from typing import List

STORE_PATH = os.path.join(os.path.dirname(__file__), "memory.json")


def _load() -> List[str]:
    if not os.path.exists(STORE_PATH):
        return []
    with open(STORE_PATH, "r") as f:
        return json.load(f)


def _save(facts: List[str]) -> None:
    with open(STORE_PATH, "w") as f:
        json.dump(facts, f, indent=2)


def remember(fact: str) -> None:
    """Persist a fact to long-term memory."""
    facts = _load()
    if fact not in facts:
        facts.append(fact)
        _save(facts)


def retrieve(query: str, top_k: int = 3) -> List[str]:
    """Naive keyword-overlap retrieval. A real system would embed
    `query` and each stored fact, then rank by cosine similarity
    (semantic search) instead of exact word overlap."""
    facts = _load()
    if not facts:
        return []

    query_words = set(re.findall(r"\w+", query.lower()))

    def score(fact: str) -> int:
        fact_words = set(re.findall(r"\w+", fact.lower()))
        return len(query_words & fact_words)

    scored = [(score(f), f) for f in facts]
    scored = [pair for pair in scored if pair[0] > 0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [fact for _, fact in scored[:top_k]]


def all_facts() -> List[str]:
    return _load()
