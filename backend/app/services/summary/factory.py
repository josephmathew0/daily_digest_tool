import os

from app.services.summary.base import SummaryProvider
from app.services.summary.fallback_provider import FallbackSummaryProvider
from app.services.summary.rule_based_provider import RuleBasedSummaryProvider


def build_summary_provider() -> SummaryProvider:
    mode = os.getenv("SUMMARY_MODE", "rules").lower()

    if mode == "rules":
        return RuleBasedSummaryProvider()
    if mode == "openai":
        from app.services.summary.openai_provider import OpenAISummaryProvider

        fallback = RuleBasedSummaryProvider()
        try:
            return FallbackSummaryProvider(OpenAISummaryProvider(), fallback)
        except Exception:
            return fallback

    raise ValueError(f"Unsupported SUMMARY_MODE={mode!r}. Supported modes: rules, openai")
