"""
Two-stage clause extractor for legal/policy documents.

Stage 1: Regex-based section detection using legal numbering patterns.
Stage 2: spaCy refinement for long sections that need sub-splitting.

Solves the problem of spaCy treating "1.2" as sentence-ending periods.
"""

import re
import warnings

try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        warnings.warn(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm. "
            "Falling back to regex-only extraction."
        )
        nlp = None
except ImportError:
    warnings.warn(
        "spaCy not installed. Falling back to regex-only extraction. "
        "Run: pip install spacy"
    )
    nlp = None


# ── Regex patterns for legal numbering (priority order) ──────────────────

CLAUSE_PATTERNS = [
    # 1. Numbered sections: "1.", "1.1", "1.2.3"
    (r"^\s*(\d+(?:\.\d+)*)\.(?:\s+|$)", "numbered"),
    # 1b. Numbered without trailing dot: "1.1 Every", "2.1 Employee", or standalone "12.4"
    (r"^\s*(\d+\.\d+(?:\.\d+)*)(?:\s+|$)", "numbered_sub"),
    # 2. Lettered/roman sub-sections: "(a)", "(ii)", "(iv)"
    (r"^\s*\(([a-z]|[ivxlc]+)\)\s+", "lettered"),
    # 3. Section headers: "Section 4", "Clause 12", "Article 5"
    (r"^\s*(Section|Clause|Article|Chapter|Part)\s+(\d+\S*)", "header"),
    # 4. Bullet points: "•", "-", "*"
    (r"^\s*[•\-\*]\s+", "bullet"),
    # 5. ALL CAPS headers: "LEAVE POLICY", "DATA PROTECTION"
    (r"^([A-Z][A-Z\s]{5,})$", "caps_header"),
]

# Compiled combined pattern for split detection
_SPLIT_PATTERN = re.compile(
    r"(?:^\s*\d+\.(?:\d+\.)*\s+)"          # numbered
    r"|(?:^\s*\([a-z]|[ivxlc]+\)\s+)"      # lettered
    r"|(?:^\s*(?:Section|Clause|Article|Chapter|Part)\s+\d+)"  # header
    r"|(?:^\s*[•\-\*]\s+)"                  # bullet
    r"|(?:^[A-Z][A-Z\s]{5,}$)",             # caps header
    re.MULTILINE,
)

MAX_CLAUSE_WORDS = 500
MIN_CLAUSE_WORDS = 10
MIN_SENTENCE_CHARS = 15


# ── Public API ───────────────────────────────────────────────────────────


def extract_clauses(text: str) -> list[dict]:
    """
    Extract clauses from legal/policy text using two-stage approach.

    Returns list of clause dicts:
    [
        {
            "index": 1,              # 1-based position
            "text": str,             # the clause text
            "section_id": str,       # detected section number or "N/A"
            "source": str,           # "regex" or "spacy"
            "word_count": int
        },
    ]
    """
    if not text or not text.strip():
        return []

    # Stage 1: regex-based splitting
    raw_sections = _regex_split(text)

    # Merge short sections with next
    merged = _merge_short_sections(raw_sections)

    # Stage 2: sub-split long sections with spaCy
    clauses = []
    for section in merged:
        word_count = len(section["text"].split())

        if word_count > MAX_CLAUSE_WORDS and nlp is not None:
            sub_sentences = _spacy_split(section["text"])
            for sent in sub_sentences:
                clauses.append({
                    "text": sent,
                    "section_id": section["section_id"],
                    "source": "spacy",
                    "word_count": len(sent.split()),
                })
        else:
            clauses.append({
                "text": section["text"],
                "section_id": section["section_id"],
                "source": "regex",
                "word_count": word_count,
            })

    # Assign 1-based indices
    for i, clause in enumerate(clauses, start=1):
        clause["index"] = i

    return clauses


def get_clause_stats(clauses: list[dict]) -> dict:
    """
    Compute summary statistics for extracted clauses.

    Returns:
    {
        "total_clauses": int,
        "avg_words_per_clause": float,
        "regex_detected": int,
        "spacy_detected": int,
        "section_ids_found": list
    }
    """
    if not clauses:
        return {
            "total_clauses": 0,
            "avg_words_per_clause": 0.0,
            "regex_detected": 0,
            "spacy_detected": 0,
            "section_ids_found": [],
        }

    total_words = sum(c["word_count"] for c in clauses)
    section_ids = [
        c["section_id"] for c in clauses
        if c["section_id"] != "N/A"
    ]
    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for sid in section_ids:
        if sid not in seen:
            seen.add(sid)
            unique_ids.append(sid)

    return {
        "total_clauses": len(clauses),
        "avg_words_per_clause": round(total_words / len(clauses), 1),
        "regex_detected": sum(1 for c in clauses if c["source"] == "regex"),
        "spacy_detected": sum(1 for c in clauses if c["source"] == "spacy"),
        "section_ids_found": unique_ids,
    }


# ── Internal: Stage 1 — Regex splitting ──────────────────────────────────


def _detect_section_id(line: str) -> str:
    """Try to extract a section identifier from a line."""
    # Numbered with trailing dot: "1.", "1.2.", "1.2.3."
    match = re.match(r"^\s*(\d+(?:\.\d+)*)\.(?:\s+|$)", line)
    if match:
        return match.group(1)

    # Numbered without trailing dot: "1.1 Every", "2.1 Employee"
    match = re.match(r"^\s*(\d+\.\d+(?:\.\d+)*)(?:\s+|$)", line)
    if match:
        return match.group(1)

    # Lettered: "(a)", "(ii)"
    match = re.match(r"^\s*\(([a-z]+|[ivxlc]+)\)\s+", line)
    if match:
        return f"({match.group(1)})"

    # Header: "Section 4", "Clause 12"
    match = re.match(
        r"^\s*(?:Section|Clause|Article|Chapter|Part)\s+(\d+\S*)",
        line, re.IGNORECASE,
    )
    if match:
        return f"Section {match.group(1)}"

    # CAPS header
    match = re.match(r"^([A-Z][A-Z\s]{5,})$", line.strip())
    if match:
        return match.group(1).strip()

    return "N/A"


def _is_boundary(line: str) -> bool:
    """Check if a line starts a new clause/section."""
    stripped = line.strip()
    if not stripped:
        return False

    for pattern, _ in CLAUSE_PATTERNS:
        if re.match(pattern, stripped, re.MULTILINE):
            return True
    return False


def _regex_split(text: str) -> list[dict]:
    """Split text into sections using legal numbering patterns."""
    lines = text.splitlines()
    sections = []
    current_lines = []
    current_id = "N/A"

    for line in lines:
        if _is_boundary(line) and current_lines:
            # Flush previous section
            section_text = "\n".join(current_lines).strip()
            if section_text:
                sections.append({
                    "text": section_text,
                    "section_id": current_id,
                })
            current_lines = [line]
            current_id = _detect_section_id(line)
        else:
            if not current_lines and not line.strip():
                continue  # skip leading blank lines
            if not current_lines:
                current_id = _detect_section_id(line)
            current_lines.append(line)

    # Flush last section
    if current_lines:
        section_text = "\n".join(current_lines).strip()
        if section_text:
            sections.append({
                "text": section_text,
                "section_id": current_id,
            })

    return sections


def _merge_short_sections(sections: list[dict]) -> list[dict]:
    """Merge sections shorter than MIN_CLAUSE_WORDS with the next section."""
    if not sections:
        return []

    merged = []
    i = 0

    while i < len(sections):
        current = sections[i].copy()
        word_count = len(current["text"].split())

        # Merge forward while too short and there is a next section
        while word_count < MIN_CLAUSE_WORDS and i + 1 < len(sections):
            i += 1
            next_section = sections[i]
            current["text"] = current["text"] + "\n" + next_section["text"]
            # When merging a short header into a real clause, adopt the
            # next section's id — the short section is just a title.
            if next_section["section_id"] != "N/A":
                current["section_id"] = next_section["section_id"]
            word_count = len(current["text"].split())

        merged.append(current)
        i += 1

    return merged


# ── Internal: Stage 2 — spaCy sub-splitting ──────────────────────────────


def _spacy_split(text: str) -> list[str]:
    """Split a long text block into sentences using spaCy."""
    if nlp is None:
        return [text]

    doc = nlp(text)
    sentences = []

    for sent in doc.sents:
        cleaned = sent.text.strip()
        if len(cleaned) >= MIN_SENTENCE_CHARS:
            sentences.append(cleaned)

    return sentences if sentences else [text]


# ── CLI test ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    test_text = """
1. LEAVE POLICY

1.1 Every employee is entitled to 30 days of annual leave per calendar year. Unused leave may be carried forward up to a maximum of 15 days.

1.2 Female employees are eligible for 12 weeks of maternity leave as per company guidelines.

(a) This leave is applicable after one year of continuous service.
(b) Paternity leave of 5 days is also available.

2. DATA HANDLING

2.1 Employee data may be shared with third-party vendors for payroll processing. No additional consent is required.

3. WORKPLACE CONDUCT

3.1 All employees must maintain professional behavior. Harassment of any kind is strictly prohibited.

GRIEVANCE REDRESSAL

Employees may raise complaints to the HR department. The HR department will resolve complaints within 30 days.
"""

    clauses = extract_clauses(test_text)
    stats = get_clause_stats(clauses)

    print(f"{'='*70}")
    print(f"CLAUSE EXTRACTION RESULTS")
    print(f"{'='*70}")

    for c in clauses:
        print(f"\n[Clause {c['index']}] section={c['section_id']}  "
              f"source={c['source']}  words={c['word_count']}")
        print(f"  {c['text'][:120]}{'...' if len(c['text']) > 120 else ''}")

    print(f"\n{'='*70}")
    print(f"STATS")
    print(f"{'='*70}")
    print(f"Total clauses:    {stats['total_clauses']}")
    print(f"Avg words/clause: {stats['avg_words_per_clause']}")
    print(f"Regex-detected:   {stats['regex_detected']}")
    print(f"spaCy-detected:   {stats['spacy_detected']}")
    print(f"Section IDs:      {stats['section_ids_found']}")
