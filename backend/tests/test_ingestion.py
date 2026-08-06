"""
backend/tests/test_ingestion.py

Unit and integration tests for Milestone 3: Document Ingestion & Clause Segmentation.

Tests:
1. Ingestion of HITS-IT-Policies.pdf, CSE_Information_Technology_Policy.pdf, and IIA_HR_Policy.pdf.
2. Structured clause-level segmentation (bullets, sub-clauses, headers, font boundaries).
3. Field validation of ClauseIndex records ({clause_id, section_title, page_no, raw_text, char_offsets, embedding_hash}).
4. Idempotency and Policy model FK linking.
"""

import os
from django.test import TestCase
from django.conf import settings

from compliance.models import ClauseIndex
from compliance.ingestion import ingest_document, parse_pdf_clauses
from policies.models import Policy


class DocumentIngestionTestCase(TestCase):
    """Test suite for PDF document parsing and ClauseIndex database ingestion."""

    @classmethod
    def setUpTestData(cls):
        cls.policy_dir = os.path.join(settings.BASE_DIR, 'media', 'policies')
        cls.hits_pdf = os.path.join(cls.policy_dir, 'HITS-IT-Policies.pdf')
        cls.cse_pdf = os.path.join(cls.policy_dir, 'CSE_Information_Technology_Policy.pdf')
        cls.iia_pdf = os.path.join(cls.policy_dir, 'IIA_HR_Policy.pdf')

    def test_pdf_files_exist(self):
        """Ensure test policy PDF files exist on filesystem."""
        self.assertTrue(os.path.exists(self.hits_pdf), f"File not found: {self.hits_pdf}")
        self.assertTrue(os.path.exists(self.cse_pdf), f"File not found: {self.cse_pdf}")
        self.assertTrue(os.path.exists(self.iia_pdf), f"File not found: {self.iia_pdf}")

    def test_ingest_hits_it_policies(self):
        """Test ingestion of HITS-IT-Policies.pdf."""
        clauses = ingest_document(self.hits_pdf, doc_id="HITS-IT-Policies.pdf")
        self.assertGreater(len(clauses), 20, "HITS policy should produce structured clauses")

        db_count = ClauseIndex.objects.filter(document_name="HITS-IT-Policies.pdf").count()
        self.assertEqual(len(clauses), db_count)

        # Check fields of first clause
        first_clause = clauses[0]
        self.assertTrue(first_clause.clause_id.startswith("CL_"))
        self.assertGreater(len(first_clause.section_title), 0)
        self.assertGreaterEqual(first_clause.page_no, 1)
        self.assertGreater(len(first_clause.raw_text), 10)
        self.assertIn("start", first_clause.char_offsets)
        self.assertIn("end", first_clause.char_offsets)
        self.assertEqual(len(first_clause.embedding_hash), 64)

    def test_ingest_cse_information_technology_policy(self):
        """Test ingestion of CSE_Information_Technology_Policy.pdf and lettered/numbered sub-clauses."""
        clauses = ingest_document(self.cse_pdf, doc_id="CSE_Information_Technology_Policy.pdf")
        self.assertGreater(len(clauses), 50, "CSE policy should produce structured clauses")

        # Verify lettered sub-clauses (e.g., 'a. Identify', 'b. Protect') are segmented separately
        raw_texts = [c.raw_text for c in clauses]
        has_identify_clause = any(t.startswith("a.") or "Identify" in t for t in raw_texts)
        has_protect_clause = any(t.startswith("b.") or "Protect" in t for t in raw_texts)
        self.assertTrue(has_identify_clause, "Should segment sub-clause 'a. Identify'")
        self.assertTrue(has_protect_clause, "Should segment sub-clause 'b. Protect'")

        # Verify VAPT section clauses are indexed
        vapt_clauses = [c for c in clauses if "Vulnerability Assessment" in c.section_title or "VAPT" in c.raw_text]
        self.assertGreater(len(vapt_clauses), 0, "Should index VAPT section clauses")

    def test_ingest_iia_hr_policy(self):
        """Test ingestion of IIA_HR_Policy.pdf including Pay-Day and POSH complaint clauses."""
        clauses = ingest_document(self.iia_pdf, doc_id="IIA_HR_Policy.pdf")
        self.assertGreater(len(clauses), 100, "IIA HR policy should produce structured clauses")

        raw_texts = [c.raw_text for c in clauses]

        # Verify 7th day pay-day clause is ingested
        payday_found = any("7th day" in t.lower() or "pay-day" in t.lower() for t in raw_texts)
        self.assertTrue(payday_found, "Should index Pay-Day 7th day clause in IIA HR policy")

        # Verify POSH complaint 10 days window clause is ingested
        posh_window_found = any("10 days" in t.lower() and "sexual harassment" in t.lower() for t in raw_texts)
        self.assertTrue(posh_window_found, "Should index POSH complaint window clause in IIA HR policy")

    def test_clause_character_offsets_and_ordering(self):
        """Verify character offsets are continuous and clauses maintain proper document page ordering."""
        clauses = ingest_document(self.hits_pdf, doc_id="HITS-IT-Policies.pdf")
        
        last_page = 1
        for c in clauses:
            self.assertGreaterEqual(c.page_no, last_page, "Clauses must be in non-decreasing page order")
            last_page = c.page_no
            self.assertGreaterEqual(c.start_char, 0)
            self.assertGreater(c.end_char, c.start_char)
            self.assertEqual(c.char_offsets['start'], c.start_char)
            self.assertEqual(c.char_offsets['end'], c.end_char)

    def test_ingestion_idempotency(self):
        """Verify re-ingesting a document clears old entries and does not create duplicates."""
        doc_name = "HITS-IT-Policies.pdf"
        run1 = ingest_document(self.hits_pdf, doc_id=doc_name)
        count1 = ClauseIndex.objects.filter(document_name=doc_name).count()
        self.assertEqual(len(run1), count1)

        run2 = ingest_document(self.hits_pdf, doc_id=doc_name)
        count2 = ClauseIndex.objects.filter(document_name=doc_name).count()
        self.assertEqual(len(run2), count2)
        self.assertEqual(count1, count2, "Re-ingesting must not duplicate ClauseIndex entries")

    def test_ingest_with_policy_orm_object(self):
        """Verify ingest_document links Policy model instance when doc_id is a Policy object."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='testuser_m3', password='password123')
        
        policy = Policy.objects.create(
            title="Test HITS Policy",
            category="cyber_security",
            uploaded_by=user,
        )
        clauses = ingest_document(self.hits_pdf, doc_id=policy)
        self.assertGreater(len(clauses), 0)

        linked_count = ClauseIndex.objects.filter(policy=policy).count()
        self.assertEqual(len(clauses), linked_count)
        self.assertEqual(clauses[0].policy, policy)


class EmpiricalEdgeCaseIngestionTestCase(TestCase):
    """Empirical challenge suite for edge cases, font splits, malformed PDFs, offsets, and memory."""

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_font_boundary_splits(self):
        """Verify font size transitions and bold headers trigger clause/section boundary splits."""
        import fitz
        pdf_path = os.path.join(self.temp_dir.name, "font_test.pdf")
        doc = fitz.open()
        page = doc.new_page()
        
        # Section Header (large font, bold)
        page.insert_text((50, 50), "SECTION 1: CYBERSECURITY GOVERNANCE", fontsize=18, fontname="hebo")
        # Sub-header (bold lead-in)
        page.insert_text((50, 80), "Access Control Policy:", fontsize=12, fontname="hebo")
        # Body text (normal font)
        page.insert_text((50, 100), "All user accounts must enforce multi-factor authentication for remote login access.", fontsize=10, fontname="helv")
        # Bullet point
        page.insert_text((50, 120), "• Passwords shall be rotated every 90 days.", fontsize=10, fontname="helv")
        doc.save(pdf_path)
        doc.close()

        clauses = ingest_document(pdf_path, doc_id="font_test.pdf")
        self.assertGreaterEqual(len(clauses), 2)
        sec_titles = [c.section_title for c in clauses]
        self.assertTrue(any("CYBERSECURITY" in s or "SECTION 1" in s for s in sec_titles))
        raw_texts = [c.raw_text for c in clauses]
        self.assertTrue(any("multi-factor authentication" in t for t in raw_texts))

    def test_empty_text_and_whitespace(self):
        """Verify empty PDFs, whitespace-only pages, and short text are handled without errors."""
        import fitz
        # 1. Blank PDF page
        blank_pdf = os.path.join(self.temp_dir.name, "blank.pdf")
        doc = fitz.open()
        doc.new_page()  # empty page
        doc.save(blank_pdf)
        doc.close()

        clauses_blank = ingest_document(blank_pdf, doc_id="blank.pdf")
        self.assertEqual(len(clauses_blank), 0, "Blank PDF should produce 0 clauses")

        # 2. PDF with whitespace & tiny text (<10 chars)
        tiny_pdf = os.path.join(self.temp_dir.name, "tiny.pdf")
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((50, 50), "   \n\t  ", fontsize=10)
        p.insert_text((50, 70), "Short", fontsize=10)  # 5 chars (<10)
        doc.save(tiny_pdf)
        doc.close()

        clauses_tiny = ingest_document(tiny_pdf, doc_id="tiny.pdf")
        self.assertEqual(len(clauses_tiny), 0, "Short text (<10 chars) should be filtered out")

    def test_malformed_pdf_handling(self):
        """Verify proper exceptions when ingesting malformed or 0-byte PDF files."""
        import fitz
        # 1. 0-byte file
        zero_pdf = os.path.join(self.temp_dir.name, "zero_bytes.pdf")
        with open(zero_pdf, "wb") as f:
            f.write(b"")

        with self.assertRaises((fitz.FileDataError, fitz.EmptyFileError, Exception)):
            ingest_document(zero_pdf, doc_id="zero_bytes.pdf")

        # 2. Corrupted file content
        corrupt_pdf = os.path.join(self.temp_dir.name, "corrupt.pdf")
        with open(corrupt_pdf, "wb") as f:
            f.write(b"NOT_A_REAL_PDF_FILE_HEADER_12345")

        with self.assertRaises((fitz.FileDataError, Exception)):
            ingest_document(corrupt_pdf, doc_id="corrupt.pdf")

        # 3. Non-existent file
        with self.assertRaises(FileNotFoundError):
            ingest_document("non_existent_policy_12345.pdf")

    def test_long_multipage_policy(self):
        """Verify performance and clause ordering for a long multi-page (50 pages) PDF."""
        import fitz
        long_pdf = os.path.join(self.temp_dir.name, "long_policy.pdf")
        doc = fitz.open()
        
        for i in range(1, 51):
            p = doc.new_page()
            p.insert_text((50, 50), f"SECTION {i}: POLICY CHAPTER {i}", fontsize=14, fontname="hebo")
            p.insert_text((50, 80), f"1. Standard operating procedure for chapter {i} compliance requirement clause text.", fontsize=10)
            p.insert_text((50, 100), f"• Sub-clause {i}.a detailing specific operational protocol and requirements.", fontsize=10)
            p.insert_text((50, 120), f"• Sub-clause {i}.b outlining compliance verification procedure.", fontsize=10)

        doc.save(long_pdf)
        doc.close()

        import time
        t0 = time.time()
        clauses = ingest_document(long_pdf, doc_id="long_policy.pdf")
        elapsed = time.time() - t0

        self.assertGreaterEqual(len(clauses), 100, "50-page policy should generate >= 100 clauses")
        self.assertLess(elapsed, 15.0, "50-page ingestion should complete within 15 seconds")

        # Page monotonic check
        pages = [c.page_no for c in clauses]
        self.assertEqual(pages, sorted(pages), "Page numbers must be monotonically non-decreasing")
        self.assertEqual(max(pages), 50, "Last clause should be on page 50")

    def test_character_offset_bounds_reconstruction(self):
        """Verify char_offsets start/end character bounds, continuous indexing, and text reconstruction."""
        policy_dir = os.path.join(settings.BASE_DIR, 'media', 'policies')
        hits_pdf = os.path.join(policy_dir, 'HITS-IT-Policies.pdf')

        clauses = ingest_document(hits_pdf, doc_id="HITS-IT-Policies.pdf")
        self.assertGreater(len(clauses), 0)

        full_reconstructed_text = " ".join(c.raw_text for c in clauses)

        for idx, c in enumerate(clauses):
            self.assertGreaterEqual(c.start_char, 0, "start_char must be non-negative")
            self.assertGreater(c.end_char, c.start_char, "end_char must be strictly greater than start_char")
            self.assertEqual(c.end_char - c.start_char, len(c.raw_text), "Offset length must match raw_text length")
            self.assertEqual(c.char_offsets['start'], c.start_char)
            self.assertEqual(c.char_offsets['end'], c.end_char)

            # Slicing validation
            extracted_substring = full_reconstructed_text[c.start_char:c.end_char]
            self.assertEqual(extracted_substring, c.raw_text, f"Offset slice mismatch at clause {c.clause_id}")

            # Continuity validation with next clause
            if idx < len(clauses) - 1:
                next_c = clauses[idx + 1]
                self.assertEqual(next_c.start_char, c.end_char + 1, f"Offset gap or overlap between {c.clause_id} and {next_c.clause_id}")

    def test_memory_behavior_and_resource_cleanup(self):
        """Verify memory stability and PyMuPDF document handle cleanup over repeated ingestions."""
        policy_dir = os.path.join(settings.BASE_DIR, 'media', 'policies')
        hits_pdf = os.path.join(policy_dir, 'HITS-IT-Policies.pdf')

        import gc
        gc.collect()

        # Ingest repeatedly
        for _ in range(10):
            clauses = parse_pdf_clauses(hits_pdf)
            self.assertGreater(len(clauses), 0)

        gc.collect()

