"""
backend/compliance/retrieval.py

Milestone 4: Multi-Model Hybrid Retrieval Engine

Features:
- Multi-model union retrieval combining top-k (k=8..10) candidates from InLegal-SBERT
  and all-MiniLM-L6-v2 via ModelRegistry.
- TF-IDF / BM25 lexical retrieval using scikit-learn for quantitative, date, and numeric queries.
- Embedding caching keyed by document version/clause hash (ClauseIndex.embedding_hash).
- Deduplicated union candidate set returned without premature truncation to top-1 prior to NLI.
"""

import hashlib
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union

from sklearn.feature_extraction.text import TfidfVectorizer

from compliance.models import ClauseIndex, Requirement, SubElement
from compliance.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Global in-memory cache for clause embeddings: (model_name, embedding_hash) -> np.ndarray
_EMBEDDING_CACHE: Dict[Tuple[str, str], np.ndarray] = {}


def clear_embedding_cache():
    """Clear the in-memory clause embedding cache."""
    global _EMBEDDING_CACHE
    _EMBEDDING_CACHE.clear()


def get_clause_embedding(
    clause_text: str,
    embedding_hash: Optional[str],
    model_name: str,
    model_instance
) -> np.ndarray:
    """
    Get vector embedding for a clause text using the specified model,
    caching vectors by model name and clause hash.
    """
    if not embedding_hash:
        embedding_hash = hashlib.sha256(clause_text.encode('utf-8')).hexdigest()

    cache_key = (model_name, embedding_hash)
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]

    # Compute embedding
    vector = model_instance.encode(clause_text, convert_to_numpy=True)
    # Ensure float32 1D numpy array
    vector = np.asarray(vector, dtype=np.float32).flatten()
    _EMBEDDING_CACHE[cache_key] = vector
    return vector


def compute_cosine_similarities(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarities between a 1D query vector and a 2D matrix of document vectors.
    """
    if doc_vecs.size == 0 or query_vec.size == 0:
        return np.array([], dtype=np.float32)

    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return np.zeros(len(doc_vecs), dtype=np.float32)

    doc_norms = np.linalg.norm(doc_vecs, axis=1)
    doc_norms[doc_norms == 0] = 1e-9  # prevent division by zero

    dots = np.dot(doc_vecs, query_vec)
    sims = dots / (doc_norms * query_norm)
    return np.clip(sims, -1.0, 1.0)


def retrieve_lexical_candidates(
    query_text: str,
    clauses: List[ClauseIndex],
    top_k: int = 8
) -> List[Tuple[ClauseIndex, float]]:
    """
    Perform TF-IDF / BM25 lexical retrieval using scikit-learn TfidfVectorizer.
    Returns list of (ClauseIndex, score) tuples.
    """
    if not clauses or not query_text.strip():
        return []

    clause_texts = [c.raw_text for c in clauses]
    corpus = [query_text] + clause_texts

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            token_pattern=r'(?u)\b\w+\b',
            ngram_range=(1, 2)
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        query_tfidf = tfidf_matrix[0:1]
        doc_tfidf = tfidf_matrix[1:]

        # Cosine similarity for TF-IDF vectors (already L2 normalized by TfidfVectorizer)
        scores = (doc_tfidf * query_tfidf.T).toarray().flatten()

        top_indices = np.argsort(scores)[::-1][:min(top_k, len(clauses))]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.0:
                results.append((clauses[idx], score))
        return results
    except Exception as exc:
        logger.warning("Lexical TF-IDF retrieval failed: %s", exc)
        return []


def retrieve_union_candidates(
    query_text: str,
    clauses: List[ClauseIndex],
    top_k: int = 8,
    include_lexical: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve top-k candidates using InLegal-SBERT, top-k candidates using all-MiniLM-L6-v2,
    and top-k candidates using TF-IDF lexical matching.
    Returns the deduplicated union candidate set with individual and combined model scores.

    Parameters:
    - query_text: str requirement/sub-element query string
    - clauses: List[ClauseIndex] document clauses to search over
    - top_k: int number of candidates to retrieve per model (default 8)
    - include_lexical: bool whether to include TF-IDF lexical retrieval in union

    Returns:
    - List[Dict[str, Any]]: Deduplicated union candidate set sorted by max similarity score.
    """
    if not clauses or not query_text.strip():
        return []

    inlegal_model = ModelRegistry.get_inlegal_sbert()
    minilm_model = ModelRegistry.get_minilm()

    # Encode query string
    query_inlegal = inlegal_model.encode(query_text, convert_to_numpy=True).flatten()
    query_minilm = minilm_model.encode(query_text, convert_to_numpy=True).flatten()

    # Encode / fetch cached embeddings for document clauses
    inlegal_doc_vecs = np.array([
        get_clause_embedding(c.raw_text, c.embedding_hash, "inlegal_sbert", inlegal_model)
        for c in clauses
    ], dtype=np.float32)

    minilm_doc_vecs = np.array([
        get_clause_embedding(c.raw_text, c.embedding_hash, "minilm", minilm_model)
        for c in clauses
    ], dtype=np.float32)

    # Compute similarity arrays
    inlegal_sims = compute_cosine_similarities(query_inlegal, inlegal_doc_vecs)
    minilm_sims = compute_cosine_similarities(query_minilm, minilm_doc_vecs)

    # Get top-k indices per model
    k_val = min(top_k, len(clauses))
    top_inlegal_idx = set(np.argsort(inlegal_sims)[::-1][:k_val])
    top_minilm_idx = set(np.argsort(minilm_sims)[::-1][:k_val])

    # Lexical TF-IDF retrieval
    lexical_dict: Dict[str, float] = {}
    if include_lexical:
        lexical_results = retrieve_lexical_candidates(query_text, clauses, top_k=k_val)
        for clause_obj, lex_score in lexical_results:
            lexical_dict[clause_obj.clause_id] = lex_score

    # Construct candidate dictionary union keyed by clause_id
    candidates_map: Dict[str, Dict[str, Any]] = {}

    for idx, c in enumerate(clauses):
        c_id = c.clause_id
        is_in_inlegal = idx in top_inlegal_idx
        is_in_minilm = idx in top_minilm_idx
        is_in_lexical = c_id in lexical_dict

        # Union condition: candidate must be selected by at least one retrieval channel
        if is_in_inlegal or is_in_minilm or is_in_lexical:
            in_score = float(inlegal_sims[idx])
            mini_score = float(minilm_sims[idx])
            lex_score = lexical_dict.get(c_id, 0.0)

            max_score = max(in_score, mini_score, lex_score)
            avg_score = (in_score + mini_score) / 2.0

            retrieved_by = []
            if is_in_inlegal:
                retrieved_by.append("inlegal")
            if is_in_minilm:
                retrieved_by.append("minilm")
            if is_in_lexical:
                retrieved_by.append("tfidf")

            candidates_map[c_id] = {
                "clause_id": c_id,
                "clause_obj": c,
                "section_title": c.section_title,
                "page_no": c.page_no,
                "raw_text": c.raw_text,
                "char_offsets": c.char_offsets,
                "start_char": c.start_char,
                "end_char": c.end_char,
                "inlegal_score": in_score,
                "minilm_score": mini_score,
                "tfidf_score": lex_score,
                "max_score": max_score,
                "avg_score": avg_score,
                "retrieved_by": retrieved_by,
            }

    # Convert map to list and sort by max_score descending
    union_candidates = list(candidates_map.values())
    union_candidates.sort(key=lambda x: x["max_score"], reverse=True)

    logger.debug(
        "Query '%s...' retrieved %d union candidates (InLegal top-%d, MiniLM top-%d, TFIDF top-%d).",
        query_text[:40], len(union_candidates), len(top_inlegal_idx), len(top_minilm_idx), len(lexical_dict)
    )
    return union_candidates


def retrieve_for_requirement(
    requirement: Requirement,
    clauses: List[ClauseIndex],
    top_k: int = 8,
    include_lexical: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve union candidate clauses for a given Requirement object.
    Combines statute_citation, title, and description for rich query representation.
    """
    query_text = f"{requirement.statute_citation}: {requirement.title}. {requirement.description}"
    return retrieve_union_candidates(query_text, clauses, top_k=top_k, include_lexical=include_lexical)


def retrieve_for_sub_element(
    sub_element: SubElement,
    clauses: List[ClauseIndex],
    top_k: int = 8,
    include_lexical: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve union candidate clauses for a given SubElement object.
    Combines requirement statute_citation and sub-element text.
    """
    query_text = f"{sub_element.requirement.statute_citation} - {sub_element.element_text}"
    return retrieve_union_candidates(query_text, clauses, top_k=top_k, include_lexical=include_lexical)
