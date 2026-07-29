"""
THEMIS Accuracy Benchmark

Evaluates rule-based checker + AI semantic matchers against labeled test data.
Computes accuracy, precision, recall, F1 for each component and combined.

Usage:
    python ml_engine/accuracy_benchmark.py
"""

import json
import os
import sys

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

import re
import numpy as np
from pathlib import Path

from laws.models import LegalRule
from ml_engine.semantic_matcher import (
    precompute_law_embeddings,
    match_clause_against_laws,
)


# ── Metrics ──────────────────────────────────────────────────────────────


def compute_metrics(y_true: list[bool], y_pred: list[bool]) -> dict:
    """Compute accuracy, precision, recall, F1 from boolean lists."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)

    total = len(y_true)
    accuracy = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall)
        else 0
    )

    return {
        "accuracy": round(accuracy, 1),
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f1": round(f1, 1),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def print_metrics(name: str, metrics: dict):
    """Print formatted metrics block."""
    print(f"\n--- {name} ---")
    print(f"Accuracy:  {metrics['accuracy']}%")
    print(f"Precision: {metrics['precision']}%")
    print(f"Recall:    {metrics['recall']}%")
    print(f"F1 Score:  {metrics['f1']}%")


def print_confusion_matrix(name: str, metrics: dict):
    """Print confusion matrix."""
    print(f"\n--- Confusion Matrix ({name}) ---")
    print(f"                Predicted Flag  Predicted OK")
    print(f"  Actual Flag        {metrics['tp']:>4}          {metrics['fn']:>4}")
    print(f"  Actual OK          {metrics['fp']:>4}          {metrics['tn']:>4}")


# ── Rule-based check (simplified for benchmark) ─────────────────────────


def rule_check_clause(clause_text: str, rules: list) -> bool:
    """
    Check if a clause triggers any rule-based flag.
    Returns True if ANY rule keyword is MISSING from the clause.
    For benchmark: we check if the clause's target rule keywords exist.
    """
    for rule in rules:
        try:
            if re.search(rule.keywords_regex, clause_text, re.IGNORECASE):
                return False  # keyword found = not flagged by rule checker
        except re.error:
            continue
    return True  # no keywords found = flagged


def rule_check_targeted(
    clause_text: str, target_law: str, target_section: str, rules: list
) -> bool:
    """
    Check if clause matches the SPECIFIC rule it should match.
    Returns True (flagged) if the targeted rule's keywords are missing.
    """
    for rule in rules:
        if rule.law_name == target_law and rule.section == target_section:
            try:
                match = re.search(
                    rule.keywords_regex, clause_text, re.IGNORECASE
                )
                return match is None  # missing = flagged
            except re.error:
                return True
    # Rule not found in DB
    return True


# ── Main benchmark ───────────────────────────────────────────────────────


def main():
    # Load test data
    data_path = Path(__file__).resolve().parent.parent / "data" / "test_clauses.json"
    with open(data_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    # Load legal rules
    rules = list(LegalRule.objects.filter(is_active=True))
    law_data = [{"id": r.id, "text": r.requirement_text} for r in rules]

    # Pre-compute law embeddings
    print("Loading models and computing law embeddings...")
    law_cache = precompute_law_embeddings(law_data)
    rule_lookup = {(r.law_name, r.section): r for r in rules}

    # Ground truth
    y_true = [tc["ground_truth_label"] for tc in test_cases]
    total = len(test_cases)
    n_flag = sum(y_true)
    n_ok = total - n_flag

    print(f"\n{'=' * 65}")
    print(f"  THEMIS ACCURACY BENCHMARK")
    print(f"{'=' * 65}")
    print(f"Test cases: {total}")
    print(f"Ground truth: {n_flag} should-flag, {n_ok} should-not-flag")

    # ── Rule-based predictions ───────────────────────────────────────
    rule_preds = []
    for tc in test_cases:
        flagged = rule_check_targeted(
            tc["clause_text"],
            tc["should_match_law"],
            tc["should_match_section"],
            rules,
        )
        rule_preds.append(flagged)

    rule_metrics = compute_metrics(y_true, rule_preds)
    print_metrics("Rule-Based Checker (targeted)", rule_metrics)

    # ── AI predictions at multiple thresholds ────────────────────────
    # Get similarities for each clause against its target rule
    miniml_scores = []
    inlegal_scores = []
    combined_scores = []

    for tc in test_cases:
        matches = match_clause_against_laws(tc["clause_text"], law_cache)

        # Find the match for the target rule
        target_rule = rule_lookup.get(
            (tc["should_match_law"], tc["should_match_section"])
        )
        target_id = target_rule.id if target_rule else None

        miniml = 0.0
        inlegal = 0.0
        combined = 0.0

        for m in matches:
            if m["legal_rule_id"] == target_id:
                miniml = m["miniml_similarity"]
                inlegal = m["inlegal_similarity"]
                combined = m["combined_score"]
                break

        miniml_scores.append(miniml)
        inlegal_scores.append(inlegal)
        combined_scores.append(combined)

    # For AI: "flagged" means clause is NOT compliant with the law
    # Logic: if clause is about the SAME topic (high similarity) but
    # ground truth says it should be flagged, the clause conflicts.
    # If ground truth says compliant, high similarity confirms compliance.
    #
    # So for AI prediction:
    # - COMPLIANT clauses have high similarity (NOT flagged)
    # - CONFLICT/GAP/MISSING clauses:
    #   * MISSING: low similarity (topic not covered)
    #   * CONFLICT/GAP: may have high similarity (same topic, wrong content)
    #
    # AI alone can't distinguish compliant from conflict when similarity
    # is high. That's why we combine with rule-based checking.

    # For standalone AI: flag if similarity is BELOW threshold
    # (indicates the clause doesn't adequately cover the requirement)
    thresholds = [0.4, 0.5, 0.6, 0.7]

    # MiniLM at default threshold
    miniml_preds_05 = [s < 0.5 for s in miniml_scores]
    miniml_metrics = compute_metrics(y_true, miniml_preds_05)
    print_metrics("MiniLM (threshold=0.5, flag if sim < threshold)", miniml_metrics)

    # InLegal-SBERT at default threshold
    inlegal_preds_05 = [s < 0.5 for s in inlegal_scores]
    inlegal_metrics = compute_metrics(y_true, inlegal_preds_05)
    print_metrics("InLegal-SBERT (threshold=0.5, flag if sim < threshold)", inlegal_metrics)

    # Combined: rule + InLegal-SBERT
    combined_preds = [
        rule_preds[i] or inlegal_scores[i] < 0.5
        for i in range(total)
    ]
    combined_metrics = compute_metrics(y_true, combined_preds)
    print_metrics("Combined (Rule + InLegal-SBERT, threshold=0.5)", combined_metrics)

    # ── Threshold analysis ───────────────────────────────────────────
    print(f"\n--- Threshold Analysis (InLegal-SBERT, flag if sim < threshold) ---")
    print(f"{'Threshold':>10} | {'Accuracy':>9} | {'Precision':>10} | {'Recall':>7} | {'F1':>6}")
    print(f"{'-'*10}-+-{'-'*9}-+-{'-'*10}-+-{'-'*7}-+-{'-'*6}")

    best_f1 = 0
    best_threshold = 0.5
    best_metrics = inlegal_metrics
    best_name = "InLegal-SBERT"

    for thresh in thresholds:
        preds = [s < thresh for s in inlegal_scores]
        m = compute_metrics(y_true, preds)
        print(
            f"    {thresh:.2f}   | {m['accuracy']:>8.1f}% | "
            f"{m['precision']:>9.1f}% | {m['recall']:>6.1f}% | {m['f1']:>5.1f}%"
        )
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_threshold = thresh
            best_metrics = m
            best_name = f"InLegal-SBERT (threshold={thresh})"

    # Also check combined at each threshold
    print(f"\n--- Threshold Analysis (Combined: Rule + InLegal-SBERT) ---")
    print(f"{'Threshold':>10} | {'Accuracy':>9} | {'Precision':>10} | {'Recall':>7} | {'F1':>6}")
    print(f"{'-'*10}-+-{'-'*9}-+-{'-'*10}-+-{'-'*7}-+-{'-'*6}")

    for thresh in thresholds:
        preds = [
            rule_preds[i] or inlegal_scores[i] < thresh
            for i in range(total)
        ]
        m = compute_metrics(y_true, preds)
        print(
            f"    {thresh:.2f}   | {m['accuracy']:>8.1f}% | "
            f"{m['precision']:>9.1f}% | {m['recall']:>6.1f}% | {m['f1']:>5.1f}%"
        )
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_threshold = thresh
            best_metrics = m
            best_name = f"Combined Rule+InLegal (threshold={thresh})"

    # ── Best model confusion matrix ──────────────────────────────────
    print_confusion_matrix(best_name, best_metrics)

    # ── Per-case details ─────────────────────────────────────────────
    print(f"\n--- Per-Case Detail (best: {best_name}) ---")
    print(f"{'ID':>3} | {'Expected':>10} | {'Rule':>5} | {'InLegal':>7} | {'Notes'}")
    print(f"{'-'*3}-+-{'-'*10}-+-{'-'*5}-+-{'-'*7}-+-{'-'*40}")

    for i, tc in enumerate(test_cases):
        expected = "FLAG" if tc["ground_truth_label"] else "OK"
        rule_flag = "FLAG" if rule_preds[i] else "OK"
        il_score = inlegal_scores[i]
        notes = tc.get("notes", "")[:40]
        print(
            f" {tc['id']:>2} | {expected:>10} | {rule_flag:>5} | "
            f"{il_score:>7.3f} | {notes}"
        )

    print(f"\n{'=' * 65}")
    print(f"  Best configuration: {best_name}")
    print(f"  F1 Score: {best_f1:.1f}%")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
