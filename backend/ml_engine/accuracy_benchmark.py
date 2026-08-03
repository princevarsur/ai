"""
THEMIS Accuracy Benchmark — v2

Evaluates all signals now available:
  1. Rule-based keyword checker
  2. MiniLM cosine similarity
  3. InLegal-SBERT cosine similarity
  4. NLI CrossEncoder (3 raw scores: contradiction, entailment, neutral)
  5. Quantity conflict checker (deterministic)
  6. Combined pipeline (all signals)

Reports accuracy/precision/recall/F1 per signal AND for the combined pipeline.
Side-by-side comparison: original 28-example set vs expanded 43-example set.
Confusion matrices for negation and quantity-conflict subsets.

Usage:
    python ml_engine/accuracy_benchmark.py
"""

import json
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

import re
import numpy as np
from pathlib import Path

import spacy
from laws.models import LegalRule
from ml_engine.semantic_matcher import precompute_law_embeddings, match_clause_against_laws
from ml_engine.contradiction_checker import batch_check_entailment
from ml_engine.quantity_checker import check_quantity_conflict


# ── Metrics ───────────────────────────────────────────────────────────────


def compute_metrics(y_true: list, y_pred: list) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    total = len(y_true)
    accuracy = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    return {
        "accuracy": round(accuracy, 1),
        "precision": round(precision, 1),
        "recall": round(recall, 1),
        "f1": round(f1, 1),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


def print_metrics(name: str, m: dict, indent: int = 0):
    pad = " " * indent
    print(f"{pad}--- {name} ---")
    print(f"{pad}  Acc={m['accuracy']}%  Prec={m['precision']}%  Rec={m['recall']}%  F1={m['f1']}%")
    print(f"{pad}  TP={m['tp']} TN={m['tn']} FP={m['fp']} FN={m['fn']}")


def print_confusion_matrix(name: str, m: dict):
    print(f"\n--- Confusion Matrix: {name} ---")
    print(f"                  Pred FLAG  Pred OK")
    print(f"  Actual FLAG       {m['tp']:>4}     {m['fn']:>4}")
    print(f"  Actual OK         {m['fp']:>4}     {m['tn']:>4}")


def print_comparison_row(label: str, m28: dict, m43: dict):
    print(
        f"  {label:<30} "
        f"F1={m28['f1']:>5.1f}%  Prec={m28['precision']:>5.1f}%  Rec={m28['recall']:>5.1f}%  |  "
        f"F1={m43['f1']:>5.1f}%  Prec={m43['precision']:>5.1f}%  Rec={m43['recall']:>5.1f}%"
    )


# ── Rule-based ────────────────────────────────────────────────────────────


def rule_check_targeted(clause_text: str, target_law: str | None,
                        target_section: str | None, rules: list) -> bool:
    """True = flagged (keyword missing from clause for the targeted rule)."""
    if not target_law or not target_section:
        return False  # no target rule = can't flag
    for rule in rules:
        if rule.law_name == target_law and rule.section == target_section:
            try:
                return re.search(rule.keywords_regex, clause_text, re.IGNORECASE) is None
            except re.error:
                return True
    return True


# ── Build feature matrix ──────────────────────────────────────────────────


def build_features(test_cases: list, rules: list, law_cache: dict, nlp) -> dict:
    """
    Compute all signals for each test case.
    Returns dict of lists, one entry per test case.
    """
    rule_lookup = {(r.law_name, r.section): r for r in rules}

    miniml_scores, inlegal_scores = [], []
    nli_contra, nli_entail, nli_neutral = [], [], []
    qty_flags, keyword_flags = [], []
    nli_labels = []

    print("  Computing semantic similarities...")
    for tc in test_cases:
        matches = match_clause_against_laws(tc["clause_text"], law_cache)
        target_rule = rule_lookup.get(
            (tc.get("should_match_law"), tc.get("should_match_section"))
        )
        target_id = target_rule.id if target_rule else None

        miniml = inlegal = 0.0
        for m in matches:
            if m["legal_rule_id"] == target_id:
                miniml = m["miniml_similarity"]
                inlegal = m["inlegal_similarity"]
                break

        miniml_scores.append(miniml)
        inlegal_scores.append(inlegal)

        kw_found = False
        if target_rule:
            try:
                kw_found = bool(
                    re.search(target_rule.keywords_regex, tc["clause_text"], re.IGNORECASE)
                )
            except re.error:
                pass
        keyword_flags.append(kw_found)

    print("  Running batch NLI inference...")
    nli_pairs = []
    for tc in test_cases:
        target_rule = rule_lookup.get(
            (tc.get("should_match_law"), tc.get("should_match_section"))
        )
        law_text = target_rule.requirement_text if target_rule else ""
        nli_pairs.append((tc["clause_text"], law_text))

    nli_results = batch_check_entailment(nli_pairs)
    for r in nli_results:
        nli_contra.append(r["raw_scores"]["contradiction"])
        nli_entail.append(r["raw_scores"]["entailment"])
        nli_neutral.append(r["raw_scores"]["neutral"])
        nli_labels.append(r["label"])

    print("  Running quantity conflict checks...")
    for i, tc in enumerate(test_cases):
        target_rule = rule_lookup.get(
            (tc.get("should_match_law"), tc.get("should_match_section"))
        )
        qty_conflict = False
        if target_rule and target_rule.required_value is not None:
            qty = check_quantity_conflict(
                tc["clause_text"],
                target_rule.required_value,
                target_rule.required_unit,
                target_rule.comparison_type,
                nlp,
            )
            qty_conflict = qty["has_quantity"] and qty["is_conflict"]
        qty_flags.append(qty_conflict)

    return {
        "miniml": miniml_scores,
        "inlegal": inlegal_scores,
        "nli_contra": nli_contra,
        "nli_entail": nli_entail,
        "nli_neutral": nli_neutral,
        "nli_label": nli_labels,
        "qty_conflict": qty_flags,
        "keyword_found": keyword_flags,
    }


# ── Signal predictions ────────────────────────────────────────────────────


def signal_preds(feats: dict, y_true: list, rules: list, test_cases: list) -> dict:
    """Compute predictions for each individual signal + combined pipeline."""
    n = len(y_true)

    # Rule-based
    rule_preds = [
        rule_check_targeted(
            tc["clause_text"],
            tc.get("should_match_law"),
            tc.get("should_match_section"),
            rules,
        )
        for tc in test_cases
    ]

    # MiniLM: flag if similarity < 0.5
    miniml_preds = [s < 0.5 for s in feats["miniml"]]

    # InLegal-SBERT: flag if similarity < 0.5
    inlegal_preds = [s < 0.5 for s in feats["inlegal"]]

    # NLI contradiction: flag if contradiction score > 0.5
    nli_preds = [s > 0.5 for s in feats["nli_contra"]]

    # Quantity conflict: flag if deterministic conflict found
    qty_preds = feats["qty_conflict"]

    # Combined pipeline (mirrors engine.py priority logic):
    #   quantity conflict → NLI contradiction → sim/keyword fallback
    combined_preds = []
    for i in range(n):
        if qty_preds[i]:
            combined_preds.append(True)
        elif feats["nli_label"][i] == "contradiction":
            combined_preds.append(True)
        elif rule_preds[i] or inlegal_preds[i]:
            combined_preds.append(True)
        else:
            combined_preds.append(False)

    return {
        "rule": rule_preds,
        "miniml": miniml_preds,
        "inlegal": inlegal_preds,
        "nli": nli_preds,
        "qty": qty_preds,
        "combined": combined_preds,
    }


# ── Main ──────────────────────────────────────────────────────────────────


def run_benchmark(test_cases: list, rules: list, law_cache: dict, nlp, label: str) -> dict:
    """Run full benchmark on a subset of test cases. Returns all per-signal metrics."""
    y_true = [tc["ground_truth_label"] for tc in test_cases]
    n = len(test_cases)
    n_flag = sum(y_true)

    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"  {n} cases | {n_flag} flagged | {n - n_flag} compliant")
    print(f"{'=' * 70}")

    feats = build_features(test_cases, rules, law_cache, nlp)
    preds = signal_preds(feats, y_true, rules, test_cases)

    signal_names = {
        "rule":     "Rule-Based Keyword Checker",
        "miniml":   "MiniLM (sim < 0.5)",
        "inlegal":  "InLegal-SBERT (sim < 0.5)",
        "nli":      "NLI CrossEncoder (contra > 0.5)",
        "qty":      "Quantity Conflict (deterministic)",
        "combined": "Combined Pipeline",
    }

    all_metrics = {}
    for key, name in signal_names.items():
        m = compute_metrics(y_true, preds[key])
        print_metrics(name, m, indent=2)
        all_metrics[key] = m

    return {"metrics": all_metrics, "feats": feats, "preds": preds, "y_true": y_true}


def main():
    data_path = Path(__file__).resolve().parent.parent / "data" / "test_clauses.json"
    with open(data_path, "r", encoding="utf-8") as f:
        all_cases = json.load(f)

    # Split: original 28 vs expanded additions (IDs 29+)
    old_cases = [tc for tc in all_cases if tc["id"] <= 28]
    new_cases = all_cases  # full 43

    rules = list(LegalRule.objects.filter(is_active=True))
    law_data = [{"id": r.id, "text": r.requirement_text} for r in rules]

    print("\nLoading models...")
    law_cache = precompute_law_embeddings(law_data)
    nlp = spacy.load("en_core_web_sm")
    print(f"Models loaded. {len(rules)} active legal rules.")

    # Run both benchmarks
    results_old = run_benchmark(old_cases, rules, law_cache, nlp, "ORIGINAL TEST SET (28 examples)")
    results_new = run_benchmark(new_cases, rules, law_cache, nlp, "EXPANDED TEST SET (43 examples)")

    # ── Side-by-side comparison ────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SIDE-BY-SIDE COMPARISON: 28 examples  vs  43 examples")
    print(f"  {'Signal':<30} {'--- Old (28) ---':>30}  {'--- New (43) ---':>30}")
    print(f"{'=' * 70}")
    signal_names = {
        "rule":     "Rule-Based Keyword",
        "miniml":   "MiniLM",
        "inlegal":  "InLegal-SBERT",
        "nli":      "NLI CrossEncoder",
        "qty":      "Quantity Conflict",
        "combined": "Combined Pipeline",
    }
    for key, name in signal_names.items():
        m_old = results_old["metrics"][key]
        m_new = results_new["metrics"][key]
        print_comparison_row(name, m_old, m_new)

    # ── Subset confusion matrices ──────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SUBSET CONFUSION MATRICES (Expanded 43-example set)")
    print(f"{'=' * 70}")

    # Negation subset
    neg_indices = [
        i for i, tc in enumerate(new_cases)
        if tc.get("category") == "negation"
    ]
    if neg_indices:
        neg_true = [results_new["y_true"][i] for i in neg_indices]
        neg_pred = [results_new["preds"]["combined"][i] for i in neg_indices]
        neg_m = compute_metrics(neg_true, neg_pred)
        print_confusion_matrix(f"Negation subset (n={len(neg_indices)})", neg_m)
        print_metrics("  Combined on negation clauses", neg_m, indent=2)

    # Wrong-number subset
    num_indices = [
        i for i, tc in enumerate(new_cases)
        if tc.get("category") == "wrong_number"
    ]
    if num_indices:
        num_true = [results_new["y_true"][i] for i in num_indices]
        num_pred_qty = [results_new["preds"]["qty"][i] for i in num_indices]
        num_pred_combined = [results_new["preds"]["combined"][i] for i in num_indices]
        qty_m = compute_metrics(num_true, num_pred_qty)
        comb_m = compute_metrics(num_true, num_pred_combined)
        print_confusion_matrix(f"Wrong-Number subset — Quantity Checker (n={len(num_indices)})", qty_m)
        print_metrics("  Quantity Checker on wrong-number clauses", qty_m, indent=2)
        print_confusion_matrix(f"Wrong-Number subset — Combined (n={len(num_indices)})", comb_m)
        print_metrics("  Combined on wrong-number clauses", comb_m, indent=2)

    # Different-wording subset
    dw_indices = [
        i for i, tc in enumerate(new_cases)
        if tc.get("category") == "different_wording"
    ]
    if dw_indices:
        dw_true = [results_new["y_true"][i] for i in dw_indices]
        dw_pred = [results_new["preds"]["combined"][i] for i in dw_indices]
        dw_m = compute_metrics(dw_true, dw_pred)
        print_confusion_matrix(f"Different-Wording subset — must NOT flag (n={len(dw_indices)})", dw_m)
        print_metrics("  Combined on different-wording clauses", dw_m, indent=2)

    # ── NLI raw score analysis on contradiction subset ─────────────────
    print(f"\n--- NLI Score Distribution on Flagged vs Compliant ---")
    flagged_contra = [
        results_new["feats"]["nli_contra"][i]
        for i, y in enumerate(results_new["y_true"]) if y
    ]
    ok_contra = [
        results_new["feats"]["nli_contra"][i]
        for i, y in enumerate(results_new["y_true"]) if not y
    ]
    if flagged_contra:
        print(f"  Flagged clauses   — NLI contradiction score: "
              f"mean={np.mean(flagged_contra):.3f}  max={max(flagged_contra):.3f}")
    if ok_contra:
        print(f"  Compliant clauses — NLI contradiction score: "
              f"mean={np.mean(ok_contra):.3f}  max={max(ok_contra):.3f}")

    # ── Best combined F1 ──────────────────────────────────────────────
    best_f1_new = results_new["metrics"]["combined"]["f1"]
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"  Combined pipeline F1 on original  28 examples: "
          f"{results_old['metrics']['combined']['f1']}%")
    print(f"  Combined pipeline F1 on expanded  43 examples: "
          f"{best_f1_new}%")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
