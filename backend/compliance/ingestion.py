"""
backend/compliance/ingestion.py

Milestone 3: Document Ingestion & Clause Segmentation Engine

Features:
- PyMuPDF (fitz) font, layout, and positional heuristics.
- Structured clause-level segmentation splitting on:
  * Bullet points (•, -, *, ▪, ✓, , , \uf0b7, \u2713, etc.)
  * Lettered/numbered sub-clauses (a), b), i., ii., 1., 2., ✓, (a), (i), etc.)
  * Section headers (font size, bold flags, ALL CAPS, explicit section titles)
  * Bold font size boundaries
- Filtering of page headers, footers, and boilerplate metadata.
- Integration with spaCy (en_core_web_sm) via ModelRegistry for sentence/clause boundary validation.
- Persistence of document-level ClauseIndex DB records:
  {clause_id, section_title, page_no, raw_text, char_offsets}.
- Function `ingest_document(pdf_path, doc_id=None)` returning list of saved ClauseIndex objects.
"""

import os
import re
import hashlib
import logging
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF
from django.db import models

from compliance.models import ClauseIndex
from compliance.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Bullet symbols regex
BULLET_PATTERN = re.compile(
    r'^\s*[\u2022\u2023\u25b6\u25c0\u25e6\u25cf\u25aa\u25ab\u25fe\u25ff\u2713\u2714\u2013\u2014\u2212\uf0b7\uf0a7\u00b7•\-\*▪✓]\s*'
)

# Sub-clause prefix patterns: a), b), a., b., i., ii., 1., 2., (a), (1), (i), etc.
SUBCLAUSE_PATTERN = re.compile(
    r'^\s*(?:'
    r'\(?[a-zA-Z][\.\)]|'                       # a), b), A), B., (a), (b)
    r'\(?\d+[\.\)]|'                             # 1., 2), 10., (1), (2)
    r'\(?(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|I|II|III|IV|V|VI|VII|VIII|IX|X)[\.\)]|' # i., ii), (iii)
    r'[✓\u2713\u2714]'                           # Checkmarks
    r')\s+'
)

# Bold title line / lead-in pattern (e.g. "Password Control:", "Scope:", "1. Importance of HR Policy")
BOLD_LEADIN_PATTERN = re.compile(
    r'^\s*(?:'
    r'[A-Z][A-Za-z0-9\s,\-\/\(\)]+:\s*|'
    r'(?:SECTION|Section|CHAPTER|Chapter|PART|Part)\s+\d+[\.\:\s]*.*|'
    r'\d+[\.\)]\s+[A-Z].*'
    r')'
)

# Known section title keywords
SECTION_KEYWORDS = {
    'overview', 'scope', 'policy', 'purpose', 'introduction', 'identify',
    'protect', 'detect', 'respond', 'recover', 'preface', 'index', 'appendix',
    'annexure', 'definitions', 'definition', 'guidelines', 'objectives',
    'responsibilities', 'background', 'disclaimer', 'amendment', 'amendments'
}


def _is_header_footer(line_text: str, bbox: tuple, page_height: float) -> bool:
    """Detect if a text line is a page header, footer, or page number boilerplate."""
    text_clean = line_text.strip()
    if not text_clean:
        return True

    # Page number patterns: "Page X of Y", "Page 1", "1 of 12"
    if re.match(r'^(?:Page\s+\d+(?:\s+of\s+\d+)?|\d+\s+of\s+\d+|\d+)$', text_clean, re.IGNORECASE):
        return True

    # Top header or bottom footer position check
    y0, y1 = bbox[1], bbox[3]
    if y0 < 40 or y1 > (page_height - 40):
        if re.search(r'(?:Policy & Procedure|Calcutta Stock Exchange|HR POLICY REVISION|HITS.*POLICIES|Ver\s+\d+\.\d+)', text_clean, re.IGNORECASE):
            return True

    return False


def _is_section_header(line_text: str, is_bold: bool, font_size: float, avg_font_size: float) -> bool:
    """Determine if a line acts as a section header based on text, font size, and bold formatting."""
    clean = line_text.strip()
    if not clean or len(clean) > 120:
        return False

    clean_lower = clean.lower()

    # Match numbered section header e.g. "1. Importance of HR Policy", "2. Objectives", "SECTION 1"
    if re.match(r'^(?:SECTION|Section|CHAPTER|Chapter|PART|Part)\s+\d+[\.\:\s]*', clean):
        return True

    if re.match(r'^\d+\.\s+[A-Z][a-zA-Z\s]{2,50}$', clean) and (is_bold or font_size > avg_font_size):
        return True

    # Check for known section keywords standing as header
    words = clean_lower.split()
    if len(words) <= 5 and any(w in SECTION_KEYWORDS for w in words):
        if is_bold or font_size >= avg_font_size:
            return True

    # Check ALL CAPS header line
    if len(clean) >= 3 and clean.isupper() and re.search(r'[A-Z]{3,}', clean):
        if is_bold or font_size >= avg_font_size:
            return True

    # Bold title ending with colon or larger font size
    if is_bold and font_size >= (avg_font_size + 1.0) and len(words) <= 8:
        return True

    return False


def parse_pdf_clauses(pdf_path: str, document_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parses PDF using PyMuPDF font/layout heuristics and spaCy sentence segmentation.
    
    Returns list of clause dicts:
    [
        {
            "clause_id": str,
            "section_title": str,
            "page_no": int,
            "raw_text": str,
            "char_offsets": {"start": int, "end": int},
            "start_char": int,
            "end_char": int,
        },
        ...
    ]
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    doc_slug = os.path.splitext(os.path.basename(pdf_path))[0]
    doc_slug = re.sub(r'[^a-zA-Z0-9]', '_', doc_slug).strip('_')

    # 1. First pass: Collect line metadata across all pages to estimate average font size
    all_lines = []
    font_sizes = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_height = page.rect.height
        blocks = page.get_text('dict').get('blocks', [])

        for block in blocks:
            if block.get('type') != 0:  # text blocks only
                continue
            for line in block.get('lines', []):
                spans = line.get('spans', [])
                if not spans:
                    continue

                line_text = "".join(span.get('text', '') for span in spans).strip()
                if not line_text:
                    continue

                # Header/footer filter
                first_span = spans[0]
                bbox = line.get('bbox', first_span.get('bbox', (0, 0, 0, 0)))
                if _is_header_footer(line_text, bbox, page_height):
                    continue

                is_bold = any(
                    bool(s.get('flags', 0) & (1 << 4)) or
                    'bold' in s.get('font', '').lower() or
                    'black' in s.get('font', '').lower() or
                    'heavy' in s.get('font', '').lower()
                    for s in spans
                )
                max_size = max(s.get('size', 10.0) for s in spans)

                all_lines.append({
                    'page_no': page_idx + 1,
                    'text': line_text,
                    'is_bold': is_bold,
                    'size': max_size,
                    'bbox': bbox,
                })
                font_sizes.append(max_size)

    avg_font_size = (sum(font_sizes) / len(font_sizes)) if font_sizes else 11.0

    # 2. Second pass: Segment lines into clauses based on layout, bullets, headers, font boundaries
    raw_clauses = []
    current_section = "General"
    current_clause_lines = []
    current_page = 1

    def emit_clause_buffer():
        nonlocal current_clause_lines, current_section, current_page
        if not current_clause_lines:
            return
        
        full_text = " ".join(current_clause_lines).strip()
        # Clean up double spaces and hyphenated linebreaks
        full_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()

        if len(full_text) >= 10:  # ignore tiny artifacts
            raw_clauses.append({
                'section_title': current_section,
                'page_no': current_page,
                'raw_text': full_text,
            })
        current_clause_lines = []

    for line_info in all_lines:
        p_no = line_info['page_no']
        text = line_info['text']
        is_bold = line_info['is_bold']
        size = line_info['size']

        # Check section header
        if _is_section_header(text, is_bold, size, avg_font_size):
            emit_clause_buffer()
            # Clean section title
            clean_sec = re.sub(r'^\d+[\.\)]\s*', '', text).strip()
            current_section = clean_sec if clean_sec else text
            current_page = p_no
            continue

        # Check bullet point boundary
        is_bullet = bool(BULLET_PATTERN.match(text))
        # Check sub-clause boundary (lettered/numbered item)
        is_subclause = bool(SUBCLAUSE_PATTERN.match(text))
        # Check bold lead-in boundary (e.g., "Password Control:", "Procurement:")
        is_bold_leadin = is_bold and bool(BOLD_LEADIN_PATTERN.match(text))

        if is_bullet or is_subclause or is_bold_leadin:
            emit_clause_buffer()
            current_page = p_no
            current_clause_lines.append(text)
        else:
            if not current_clause_lines:
                current_page = p_no
            current_clause_lines.append(text)

    # Emit final buffer
    emit_clause_buffer()

    # 3. Third pass: Refine raw clauses with spaCy for multi-sentence blocks & calculate character offsets
    spacy_nlp = ModelRegistry.get_spacy()

    refined_clauses = []
    clause_counter = 1
    cumulative_char_offset = 0

    for item in raw_clauses:
        sec_title = item['section_title']
        p_no = item['page_no']
        text = item['raw_text']

        # If a non-bullet clause contains multiple complete policy sentences, split into atomic clauses using spaCy
        has_bullet_prefix = (
            BULLET_PATTERN.match(text) or
            SUBCLAUSE_PATTERN.match(text) or
            BOLD_LEADIN_PATTERN.match(text)
        )

        sub_texts = []
        if not has_bullet_prefix and len(text) > 250:
            doc_spacy = spacy_nlp(text)
            sents = [sent.text.strip() for sent in doc_spacy.sents if len(sent.text.strip()) >= 15]
            if len(sents) > 1:
                sub_texts = sents
            else:
                sub_texts = [text]
        else:
            sub_texts = [text]

        for sub_t in sub_texts:
            start_offset = cumulative_char_offset
            end_offset = start_offset + len(sub_t)
            
            c_id = f"CL_{clause_counter:03d}"
            refined_clauses.append({
                'clause_id': c_id,
                'section_title': sec_title,
                'page_no': p_no,
                'raw_text': sub_t,
                'char_offsets': {'start': start_offset, 'end': end_offset},
                'start_char': start_offset,
                'end_char': end_offset,
            })

            clause_counter += 1
            # Advance cumulative offset (+1 for space separator in document text stream)
            cumulative_char_offset = end_offset + 1

    logger.info(
        "Parsed %d structured clauses from '%s' across %d pages.",
        len(refined_clauses), pdf_path, len(doc)
    )
    return refined_clauses


def ingest_document(pdf_path: str, doc_id: Any = None) -> List[ClauseIndex]:
    """
    Parses a PDF policy document into structured clause-level segments using PyMuPDF
    layout/font heuristics and spaCy (en_core_web_sm), creates ClauseIndex objects
    in the database, and returns the list of indexed clauses.

    Parameters:
    - pdf_path: str or Path to the PDF file.
    - doc_id: Optional string document name, int Policy ID, or Policy model instance.

    Returns:
    - List[ClauseIndex]: List of created ClauseIndex ORM objects.
    """
    pdf_path_str = str(pdf_path)

    policy_obj = None
    if doc_id is not None:
        if isinstance(doc_id, str):
            document_name = doc_id
            # Try linking policy by title or filename match if available
            try:
                from policies.models import Policy
                policy_obj = Policy.objects.filter(
                    models.Q(title=doc_id) | models.Q(file__icontains=os.path.basename(pdf_path_str))
                ).first()
            except Exception:
                policy_obj = None
        elif isinstance(doc_id, int):
            try:
                from policies.models import Policy
                policy_obj = Policy.objects.filter(id=doc_id).first()
                document_name = policy_obj.title if policy_obj else os.path.basename(pdf_path_str)
            except Exception:
                policy_obj = None
                document_name = os.path.basename(pdf_path_str)
        elif hasattr(doc_id, 'id') and hasattr(doc_id, 'title'):
            policy_obj = doc_id
            document_name = getattr(doc_id, 'title', os.path.basename(pdf_path_str))
        else:
            document_name = str(doc_id)
    else:
        document_name = os.path.basename(pdf_path_str)

    # Clean previous ClauseIndex entries for this document/policy for clean idempotency
    if policy_obj:
        ClauseIndex.objects.filter(policy=policy_obj).delete()
    ClauseIndex.objects.filter(document_name=document_name).delete()

    # Parse clauses from PDF
    parsed_clauses = parse_pdf_clauses(pdf_path_str, document_name=document_name)

    # Persist ClauseIndex objects
    clause_objects = []
    for item in parsed_clauses:
        raw_text = item['raw_text']
        emb_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()

        ci = ClauseIndex(
            document_name=document_name,
            policy=policy_obj,
            clause_id=item['clause_id'],
            section_title=item['section_title'],
            page_no=item['page_no'],
            raw_text=raw_text,
            char_offsets=item['char_offsets'],
            start_char=item['start_char'],
            end_char=item['end_char'],
            embedding_hash=emb_hash,
        )
        clause_objects.append(ci)

    created_records = ClauseIndex.objects.bulk_create(clause_objects)
    logger.info("Successfully ingested %d ClauseIndex records for '%s'.", len(created_records), document_name)
    return created_records
