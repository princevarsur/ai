"""
ml_engine/contradiction_checker.py

NLI-based contradiction / entailment detection using a CrossEncoder model.
Loaded once at module level — subsequent calls are fast batched inference.

Model: cross-encoder/nli-MiniLM2-L6-H768 (~90MB, 3-class NLI)
Labels: contradiction / entailment / neutral
"""

from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)

# ─── Module-level model loading ───────────────────────────────────────────

print("Loading NLI CrossEncoder (nli-MiniLM2-L6-H768)...")
try:
    from sentence_transformers import CrossEncoder
    nli_model = CrossEncoder("cross-encoder/nli-MiniLM2-L6-H768")
    print("NLI model loaded.")
except Exception as _e:
    nli_model = None
    logger.error("Failed to load NLI model: %s", _e)
    print(f"WARNING: NLI model not loaded — {_e}")

# Model outputs scores in this order: contradiction, entailment, neutral
LABEL_MAPPING = ["contradiction", "entailment", "neutral"]


# ─── Core functions ───────────────────────────────────────────────────────


def check_entailment(clause_text: str, law_requirement_text: str, clause_as_premise: bool = False) -> dict:
    """
    Run the NLI model on (clause_text, law_requirement_text).

    The model asks: given the law requirement as the *premise*, does the
    policy clause *entail*, *contradict*, or stay *neutral* to it?

    Args:
        clause_text: The policy clause (hypothesis).
        law_requirement_text: The legal requirement (premise).
        clause_as_premise: When checking element satisfaction, clause is premise and requirement is hypothesis.

    Returns:
        {
            "label": str,          # "contradiction" | "entailment" | "neutral"
            "confidence": float,   # softmax probability of the winning label
            "raw_scores": {
                "contradiction": float,
                "entailment": float,
                "neutral": float,
            }
        }
    """
    if nli_model is None:
        return {
            "label": "neutral",
            "confidence": 0.0,
            "raw_scores": {"contradiction": 0.0, "entailment": 0.0, "neutral": 1.0},
        }

    pair = (clause_text, law_requirement_text) if clause_as_premise else (law_requirement_text, clause_text)
    raw = nli_model.predict([pair])
    scores = _softmax(raw[0])

    best_idx = int(np.argmax(scores))
    label = LABEL_MAPPING[best_idx]
    confidence = float(scores[best_idx])

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "raw_scores": {
            "contradiction": round(float(scores[0]), 4),
            "entailment": round(float(scores[1]), 4),
            "neutral": round(float(scores[2]), 4),
        },
    }


def batch_check_entailment(pairs: list[tuple[str, str]], clause_as_premise: bool = False) -> list[dict]:
    """
    Run NLI over a list of (clause_text, law_requirement_text) pairs in one batch.
    Faster than calling check_entailment in a loop.

    Returns:
        List of result dicts matching check_entailment() format,
        in the same order as `pairs`.
    """
    if not pairs:
        return []

    if nli_model is None:
        return [
            {
                "label": "neutral",
                "confidence": 0.0,
                "raw_scores": {
                    "contradiction": 0.0,
                    "entailment": 0.0,
                    "neutral": 1.0,
                },
            }
            for _ in pairs
        ]

    # Flip to (premise=law, hypothesis=clause) for each pair
    model_pairs = [(clause, law) if clause_as_premise else (law, clause) for clause, law in pairs]
    raw_batch = nli_model.predict(model_pairs)

    results = []
    for raw in raw_batch:
        scores = _softmax(raw)
        best_idx = int(np.argmax(scores))
        results.append({
            "label": LABEL_MAPPING[best_idx],
            "confidence": round(float(scores[best_idx]), 4),
            "raw_scores": {
                "contradiction": round(float(scores[0]), 4),
                "entailment": round(float(scores[1]), 4),
                "neutral": round(float(scores[2]), 4),
            },
        })

    return results


# ─── Utility ──────────────────────────────────────────────────────────────


def _softmax(logits) -> np.ndarray:
    """Stable softmax for 1-D logit array."""
    x = np.array(logits, dtype=np.float64)
    x -= x.max()
    e = np.exp(x)
    return e / e.sum()


# ─── Self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_pairs = [
        (
            "The company does not have an Internal Complaints Committee",
            "Every employer must constitute an Internal Complaints Committee",
            "contradiction",
        ),
        (
            "The company has constituted an Internal Complaints Committee "
            "with a Presiding Officer",
            "Every employer must constitute an Internal Complaints Committee",
            "entailment",
        ),
        (
            "Working hours are 9am to 6pm",
            "Every employer must constitute an Internal Complaints Committee",
            "neutral",
        ),
        (
            "Female employees are entitled to 12 weeks of maternity leave",
            "Every female employee is entitled to at least 26 weeks of paid maternity leave",
            "contradiction",
        ),
        (
            "Employee personal data may be shared with third parties without consent",
            "Personal data shall be processed only after obtaining explicit consent from the data principal",
            "contradiction",
        ),
    ]

    print("\n=== NLI Self-Test ===")
    passed = 0
    for clause, law, expected in test_pairs:
        result = check_entailment(clause, law)
        ok = result["label"] == expected
        status = "OK" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"\n  [{status}] Expected: {expected!r}")
        print(f"  Clause: {clause[:80]!r}")
        print(f"  Law:    {law[:80]!r}")
        print(f"  Result: label={result['label']!r} confidence={result['confidence']:.3f}")
        print(f"  Scores: contra={result['raw_scores']['contradiction']:.3f}  "
              f"entail={result['raw_scores']['entailment']:.3f}  "
              f"neutral={result['raw_scores']['neutral']:.3f}")

    print(f"\n=== {passed}/{len(test_pairs)} tests passed ===")
