"""
Semantic similarity engine for legal compliance checking.

Uses two sentence-transformer models:
  1. MiniLM (fast, general English)
  2. InLegal-SBERT (Indian legal domain, higher weight)

Pre-computes law embeddings once, then batch-matches clauses efficiently.
"""

import os
import sys
import warnings

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    warnings.warn(
        "sentence-transformers not installed. "
        "Run: pip install sentence-transformers"
    )
    SentenceTransformer = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    warnings.warn("scikit-learn not installed. Run: pip install scikit-learn")
    cosine_similarity = None


# ── Model loading (once at import time) ──────────────────────────────────

FAST_MODEL_NAME = "all-MiniLM-L6-v2"
LEGAL_MODEL_NAME = "bhavyagiri/InLegal-Sbert"

# Weight InLegal-SBERT higher — better for Indian legal text
FAST_WEIGHT = 0.4
LEGAL_WEIGHT = 0.6

CONFLICT_THRESHOLD = 0.6

fast_model = None
legal_model = None


def _load_models():
    """Load both models via ModelRegistry singleton (local cache first)."""
    global fast_model, legal_model
    try:
        from compliance.model_registry import ModelRegistry
        fast_model = ModelRegistry.get_minilm()
        legal_model = ModelRegistry.get_inlegal_sbert()
        print("Both models loaded successfully from ModelRegistry.")
        return
    except Exception as e:
        print("ModelRegistry loading fallback:", e)

    if SentenceTransformer is None:
        raise ImportError("sentence-transformers is required but not installed.")

    if fast_model is None:
        print(f"Loading MiniLM model ({FAST_MODEL_NAME})...")
        try:
            fast_model = SentenceTransformer(FAST_MODEL_NAME, local_files_only=True)
        except Exception:
            fast_model = SentenceTransformer(FAST_MODEL_NAME)
        print("MiniLM loaded.")

    if legal_model is None:
        print(f"Loading InLegal-SBERT model ({LEGAL_MODEL_NAME})...")
        try:
            legal_model = SentenceTransformer(LEGAL_MODEL_NAME, local_files_only=True)
        except Exception:
            legal_model = SentenceTransformer(LEGAL_MODEL_NAME)
        print("InLegal-SBERT loaded.")

    print("Both models loaded successfully.")


def _ensure_models():
    """Ensure models are loaded before use."""
    if fast_model is None or legal_model is None:
        _load_models()


# ── Public API ───────────────────────────────────────────────────────────


def precompute_law_embeddings(law_requirements: list[dict]) -> dict:
    """
    Pre-compute embeddings for all law requirement texts.

    Args:
        law_requirements: list of {"id": int, "text": str}

    Returns:
    {
        "fast_embeddings": np.ndarray,   # shape (n_laws, embedding_dim)
        "legal_embeddings": np.ndarray,
        "law_ids": list[int],
        "law_texts": list[str],
    }
    """
    _ensure_models()

    if not law_requirements:
        return {
            "fast_embeddings": np.array([]),
            "legal_embeddings": np.array([]),
            "law_ids": [],
            "law_texts": [],
        }

    texts = [r["text"] for r in law_requirements]
    ids = [r["id"] for r in law_requirements]

    # Batch encode all law texts at once
    fast_embeddings = fast_model.encode(texts, show_progress_bar=False)
    legal_embeddings = legal_model.encode(texts, show_progress_bar=False)

    return {
        "fast_embeddings": np.array(fast_embeddings),
        "legal_embeddings": np.array(legal_embeddings),
        "law_ids": ids,
        "law_texts": texts,
    }


def match_clause_against_laws(
    clause_text: str, law_cache: dict
) -> list[dict]:
    """
    Compare one clause against all law requirements using both models.

    Returns matches with similarity > 0.3 from either model,
    sorted by combined_score descending.
    """
    _ensure_models()

    if not law_cache.get("law_ids"):
        return []

    # Encode single clause
    fast_vec = fast_model.encode([clause_text], show_progress_bar=False)
    legal_vec = legal_model.encode([clause_text], show_progress_bar=False)

    # Compute cosine similarity against all laws
    fast_sims = cosine_similarity(fast_vec, law_cache["fast_embeddings"])[0]
    legal_sims = cosine_similarity(legal_vec, law_cache["legal_embeddings"])[0]

    return _build_matches(fast_sims, legal_sims, law_cache, threshold=0.3)


def batch_match_clauses(
    clauses: list[dict],
    law_cache: dict,
    similarity_threshold: float = 0.4,
) -> list[dict]:
    """
    Match ALL clauses against ALL laws efficiently using batch encoding.

    Args:
        clauses: list of clause dicts from clause_extractor
        law_cache: pre-computed law embeddings
        similarity_threshold: minimum combined score to include

    Returns list of clause match results with all matching laws.
    """
    _ensure_models()

    if not clauses or not law_cache.get("law_ids"):
        return []

    clause_texts = [c["text"] for c in clauses]

    # Batch encode ALL clauses at once (10x faster than one-by-one)
    fast_vecs = fast_model.encode(clause_texts, show_progress_bar=False)
    legal_vecs = legal_model.encode(clause_texts, show_progress_bar=False)

    # Compute similarity matrices: (n_clauses, n_laws)
    fast_sim_matrix = cosine_similarity(
        np.array(fast_vecs), law_cache["fast_embeddings"]
    )
    legal_sim_matrix = cosine_similarity(
        np.array(legal_vecs), law_cache["legal_embeddings"]
    )

    results = []

    for i, clause in enumerate(clauses):
        matches = _build_matches(
            fast_sim_matrix[i],
            legal_sim_matrix[i],
            law_cache,
            threshold=similarity_threshold,
        )

        results.append({
            "clause_index": clause.get("index", i + 1),
            "clause_text": clause["text"],
            "matches": matches,
        })

    return results


# ── Internal ─────────────────────────────────────────────────────────────


def _build_matches(
    fast_sims: np.ndarray,
    legal_sims: np.ndarray,
    law_cache: dict,
    threshold: float = 0.3,
) -> list[dict]:
    """Build sorted match list from similarity vectors."""
    matches = []

    for j, law_id in enumerate(law_cache["law_ids"]):
        fast_score = float(fast_sims[j])
        legal_score = float(legal_sims[j])
        combined = FAST_WEIGHT * fast_score + LEGAL_WEIGHT * legal_score

        # Include if either model shows meaningful similarity
        if fast_score >= threshold or legal_score >= threshold:
            matches.append({
                "legal_rule_id": law_id,
                "miniml_similarity": round(fast_score, 4),
                "inlegal_similarity": round(legal_score, 4),
                "combined_score": round(combined, 4),
                "is_potential_conflict": combined > CONFLICT_THRESHOLD,
            })

    matches.sort(key=lambda m: m["combined_score"], reverse=True)
    return matches


# ── CLI test ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import django
    django.setup()

    from laws.models import LegalRule

    # Load all active laws
    rules = LegalRule.objects.filter(is_active=True)
    law_requirements = [
        {"id": r.id, "text": r.requirement_text} for r in rules
    ]
    print(f"Loaded {len(law_requirements)} active legal rules.\n")

    # Pre-compute law embeddings
    law_cache = precompute_law_embeddings(law_requirements)
    print(f"Law embeddings cached: fast={law_cache['fast_embeddings'].shape}, "
          f"legal={law_cache['legal_embeddings'].shape}\n")

    # Build law_id to rule lookup
    rule_lookup = {r.id: r for r in rules}

    # Test clauses
    test_clauses = [
        "Female employees get 12 weeks maternity leave",
        "Employee data may be shared with third-party vendors",
        "Working hours are 9am to 6pm, Monday to Friday",
    ]

    print("=" * 80)
    print("SEMANTIC MATCHING RESULTS")
    print("=" * 80)

    for clause_text in test_clauses:
        print(f"\nClause: \"{clause_text}\"")
        print("-" * 80)
        print(f"  {'Law':<45} {'MiniLM':>8} {'InLegal':>8} {'Combined':>9} {'Conflict':>9}")
        print(f"  {'-'*45} {'-'*8} {'-'*8} {'-'*9} {'-'*9}")

        matches = match_clause_against_laws(clause_text, law_cache)

        if not matches:
            print("  No matches above threshold.")
            continue

        for m in matches[:5]:  # top 5
            rule = rule_lookup.get(m["legal_rule_id"])
            law_label = f"{rule.law_name} {rule.section}" if rule else f"ID={m['legal_rule_id']}"
            conflict = "YES" if m["is_potential_conflict"] else ""
            print(
                f"  {law_label:<45} "
                f"{m['miniml_similarity']:>8.4f} "
                f"{m['inlegal_similarity']:>8.4f} "
                f"{m['combined_score']:>9.4f} "
                f"{conflict:>9}"
            )

    # Test batch matching
    print(f"\n{'=' * 80}")
    print("BATCH MATCHING TEST")
    print("=" * 80)

    clause_dicts = [
        {"index": i + 1, "text": t} for i, t in enumerate(test_clauses)
    ]
    batch_results = batch_match_clauses(clause_dicts, law_cache, similarity_threshold=0.4)

    for br in batch_results:
        match_count = len(br["matches"])
        conflict_count = sum(1 for m in br["matches"] if m["is_potential_conflict"])
        print(
            f"  Clause {br['clause_index']}: "
            f"{match_count} matches, {conflict_count} potential conflicts"
        )
