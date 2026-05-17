import os

from app.services.extraction.base import ExtractionProvider
from app.services.extraction.fallback_provider import FallbackExtractionProvider
from app.services.extraction.rule_based_provider import RuleBasedExtractionProvider


def build_extraction_provider() -> ExtractionProvider:
    mode = os.getenv("EXTRACTION_MODE", "rules").lower()

    if mode == "rules":
        return RuleBasedExtractionProvider()
    if mode == "openai":
        from app.services.extraction.openai_provider import OpenAIExtractionProvider

        fallback = RuleBasedExtractionProvider()
        try:
            return FallbackExtractionProvider(OpenAIExtractionProvider(), fallback)
        except Exception:
            return fallback
    if mode == "hybrid":
        from app.services.extraction.hybrid_provider import HybridExtractionProvider

        fallback = RuleBasedExtractionProvider()
        try:
            return FallbackExtractionProvider(HybridExtractionProvider(), fallback)
        except Exception:
            return fallback

    # Keep unsupported modes explicit so we do not silently spend money or skip extraction.
    raise ValueError(f"Unsupported EXTRACTION_MODE={mode!r}. Supported modes: rules, openai, hybrid")
