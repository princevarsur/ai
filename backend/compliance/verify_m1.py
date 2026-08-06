"""
Verification script for Milestone 1: Models & Registry Singleton
"""
import os
import sys
import threading
import django

# Add backend to path and setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from compliance.model_registry import ModelRegistry
from compliance.models import Requirement, SubElement, ClauseIndex, AuditFinding


def test_model_registry_offline():
    print("--- 1. Testing ModelRegistry Singleton & Model Loading ---")
    
    # 1. spaCy
    nlp = ModelRegistry.get_spacy()
    assert nlp is not None, "spaCy model failed to load"
    print("[OK] spaCy loaded:", type(nlp).__name__, nlp.meta.get("name"))

    # 2. InLegal-SBERT
    inlegal = ModelRegistry.get_inlegal_sbert()
    assert inlegal is not None, "InLegal-SBERT model failed to load"
    print("[OK] InLegal-SBERT loaded:", type(inlegal).__name__)

    # 3. MiniLM
    minilm = ModelRegistry.get_minilm()
    assert minilm is not None, "MiniLM model failed to load"
    print("[OK] MiniLM loaded:", type(minilm).__name__)

    # 4. NLI Cross-Encoder
    nli = ModelRegistry.get_nli_cross_encoder()
    assert nli is not None, "NLI Cross-Encoder failed to load"
    print("[OK] NLI Cross-Encoder loaded:", type(nli).__name__)

    # 5. GLiNER
    gliner = ModelRegistry.get_gliner()
    assert gliner is not None, "GLiNER model failed to load"
    print("[OK] GLiNER loaded:", type(gliner).__name__)

    # Singleton instance identity check
    inst1 = ModelRegistry.get_instance()
    inst2 = ModelRegistry.get_instance()
    assert inst1 is inst2, "ModelRegistry singleton instance mismatch!"
    print("[OK] ModelRegistry singleton instance verified")


def test_model_registry_thread_safety():
    print("\n--- 2. Testing Thread Safety under Concurrency ---")
    errors = []

    def worker(worker_id):
        try:
            sp = ModelRegistry.get_spacy()
            sb = ModelRegistry.get_inlegal_sbert()
            ml = ModelRegistry.get_minilm()
            nl = ModelRegistry.get_nli_cross_encoder()
            gl = ModelRegistry.get_gliner()
            assert sp is not None and sb is not None and ml is not None and nl is not None and gl is not None
        except Exception as e:
            errors.append((worker_id, e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety test failed with errors: {errors}"
    print("[OK] Thread safety verified across 10 concurrent threads")


def test_v2_django_models():
    print("\n--- 3. Testing v2 Django Models CRUD Operations ---")
    
    # Create Requirement
    req = Requirement.objects.create(
        statute_citation="TEST Act 2026 Section 1",
        title="Test Requirement",
        description="Testing v2 model implementation",
        taxonomy_type="composite",
        penalty_tier="high",
        mandatory_weight=1.0,
        domain="labour",
    )
    print("[OK] Created Requirement:", req)

    # Create SubElement
    sub = SubElement.objects.create(
        requirement=req,
        element_key="test_key_1",
        element_text="Test sub-element text",
        weight=0.5,
        gliner_label="role/designation",
    )
    print("[OK] Created SubElement:", sub)

    # Create ClauseIndex
    clause = ClauseIndex.objects.create(
        document_name="test_doc.pdf",
        clause_id="CL_TEST_001",
        section_title="Test Section",
        page_no=1,
        raw_text="The company shall comply with test rules.",
        char_offsets={"start": 0, "end": 42},
        start_char=0,
        end_char=42,
    )
    print("[OK] Created ClauseIndex:", clause)

    # Create AuditFinding
    finding = AuditFinding.objects.create(
        requirement=req,
        verdict="GAP",
        confidence_tier="High",
        severity_score=65.0,
        coverage=0.5,
        nli_confidence=0.88,
        evidence_clauses=[{"clause_id": clause.clause_id, "text": clause.raw_text}],
        sub_element_status=[{"key": sub.element_key, "status": "MISSING", "weight": 0.5}],
    )
    print("[OK] Created AuditFinding:", finding)

    # Clean up test records
    finding.delete()
    clause.delete()
    sub.delete()
    req.delete()
    print("[OK] Cleaned up test records successfully")


if __name__ == "__main__":
    print("==========================================")
    print("   Milestone 1 Verification Suite")
    print("==========================================")
    test_model_registry_offline()
    test_model_registry_thread_safety()
    test_v2_django_models()
    print("\n==========================================")
    print("   ALL MILESTONE 1 VERIFICATIONS PASSED!")
    print("==========================================")
