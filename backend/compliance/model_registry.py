"""
backend/compliance/model_registry.py

Thread-safe singleton (`ModelRegistry`) providing getter methods for all 5 local ML models:
- spaCy (en_core_web_sm)
- InLegal-SBERT (bhavyagiri/InLegal-Sbert)
- all-MiniLM-L6-v2 (sentence-transformers/all-MiniLM-L6-v2)
- NLI CrossEncoder (cross-encoder/nli-MiniLM2-L6-H768)
- GLiNER (urchade/gliner_small-v2)

Uses local_files_only=True and HF_HUB_OFFLINE=1 fallback to ensure 100% local offline loading.
"""

import os
import logging
import threading
from typing import Optional

# Enforce offline mode for HuggingFace Transformers & Hub
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

logger = logging.getLogger(__name__)


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None
    _singleton_lock = threading.Lock()

    def __init__(self):
        # Cached model instances
        self._spacy_nlp = None
        self._inlegal_sbert = None
        self._minilm = None
        self._nli_cross_encoder = None
        self._gliner = None

        # Fine-grained thread locks per model
        self._spacy_lock = threading.Lock()
        self._inlegal_lock = threading.Lock()
        self._minilm_lock = threading.Lock()
        self._nli_lock = threading.Lock()
        self._gliner_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get or create the thread-safe singleton instance."""
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_spacy(cls):
        """Load and return spaCy en_core_web_sm model."""
        inst = cls.get_instance()
        if inst._spacy_nlp is None:
            with inst._spacy_lock:
                if inst._spacy_nlp is None:
                    import spacy
                    logger.info("Loading spaCy model 'en_core_web_sm'...")
                    inst._spacy_nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model loaded successfully.")
        return inst._spacy_nlp

    @classmethod
    def get_inlegal_sbert(cls):
        """Load and return InLegal-SBERT SentenceTransformer model."""
        inst = cls.get_instance()
        if inst._inlegal_sbert is None:
            with inst._inlegal_lock:
                if inst._inlegal_sbert is None:
                    from sentence_transformers import SentenceTransformer
                    model_name = "bhavyagiri/InLegal-Sbert"
                    logger.info("Loading InLegal-SBERT (%s)...", model_name)
                    try:
                        inst._inlegal_sbert = SentenceTransformer(model_name, local_files_only=True)
                    except TypeError:
                        inst._inlegal_sbert = SentenceTransformer(model_name)
                    logger.info("InLegal-SBERT loaded successfully.")
        return inst._inlegal_sbert

    @classmethod
    def get_minilm(cls):
        """Load and return all-MiniLM-L6-v2 SentenceTransformer model."""
        inst = cls.get_instance()
        if inst._minilm is None:
            with inst._minilm_lock:
                if inst._minilm is None:
                    from sentence_transformers import SentenceTransformer
                    model_name = "sentence-transformers/all-MiniLM-L6-v2"
                    logger.info("Loading MiniLM (%s)...", model_name)
                    try:
                        inst._minilm = SentenceTransformer(model_name, local_files_only=True)
                    except Exception:
                        try:
                            inst._minilm = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
                        except Exception:
                            inst._minilm = SentenceTransformer(model_name)
                    logger.info("MiniLM loaded successfully.")
        return inst._minilm

    @classmethod
    def get_nli_cross_encoder(cls):
        """Load and return NLI CrossEncoder model."""
        inst = cls.get_instance()
        if inst._nli_cross_encoder is None:
            with inst._nli_lock:
                if inst._nli_cross_encoder is None:
                    from sentence_transformers import CrossEncoder
                    model_name = "cross-encoder/nli-MiniLM2-L6-H768"
                    logger.info("Loading NLI CrossEncoder (%s)...", model_name)
                    try:
                        inst._nli_cross_encoder = CrossEncoder(model_name, local_files_only=True)
                    except Exception:
                        inst._nli_cross_encoder = CrossEncoder(model_name)
                    logger.info("NLI CrossEncoder loaded successfully.")
        return inst._nli_cross_encoder

    @classmethod
    def get_gliner(cls):
        """Load and return GLiNER model."""
        inst = cls.get_instance()
        if inst._gliner is None:
            with inst._gliner_lock:
                if inst._gliner is None:
                    from gliner import GLiNER
                    model_name = "urchade/gliner_small-v2"
                    logger.info("Loading GLiNER (%s)...", model_name)
                    try:
                        inst._gliner = GLiNER.from_pretrained(model_name, local_files_only=True)
                    except Exception:
                        inst._gliner = GLiNER.from_pretrained(model_name)
                    logger.info("GLiNER loaded successfully.")
        return inst._gliner

    @classmethod
    def warmup(cls) -> dict:
        """Eagerly load all 5 ML models into memory."""
        logger.info("Warming up ModelRegistry (pre-loading all 5 ML models)...")
        results = {}
        for name, getter in [
            ("spacy", cls.get_spacy),
            ("inlegal_sbert", cls.get_inlegal_sbert),
            ("minilm", cls.get_minilm),
            ("nli_cross_encoder", cls.get_nli_cross_encoder),
            ("gliner", cls.get_gliner),
        ]:
            try:
                model = getter()
                results[name] = model is not None
            except Exception as exc:
                logger.error("Failed to warmup model %s: %s", name, exc)
                results[name] = False
        logger.info("ModelRegistry warmup completed: %s", results)
        return results
