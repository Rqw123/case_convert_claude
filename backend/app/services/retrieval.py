"""
Candidate signal retrieval service.
Rule-based keyword matching with synonym expansion.
"""
import re
from typing import Dict, List, Tuple
from app.schemas.schemas import FlatSignal, NormalizedCaseSemantics
from app.services.normalizer import (
    ACTION_OPEN, ACTION_CLOSE, ACTION_LOCK, ACTION_UNLOCK,
    POSITION_ALIASES, RANGE_EXPANSION, ENUM_LEVEL_PATTERNS,
)

TOP_N = 15  # Max candidates per case


def _keywords_from_text(text: str) -> List[str]:
    """Extract meaningful keywords from text."""
    # Remove common particles
    clean = re.sub(r'[，。！？、；：""''【】（）()：\s]', ' ', text)
    tokens = [t.strip() for t in clean.split() if t.strip() and len(t.strip()) > 0]
    # Also keep individual chars that might be meaningful (CJK)
    chars = re.findall(r'[\u4e00-\u9fff]{2,}', text)
    return list(set(tokens + chars))


def _score_signal(signal: FlatSignal, keywords: List[str]) -> float:
    """Score a signal against a list of keywords."""
    score = 0.0
    search_fields = [
        (signal.signal_name or "", 3.0),
        (signal.signal_desc or "", 2.5),
        (signal.message_name or "", 1.5),
        (" ".join(signal.values.values()), 1.5),
        (" ".join(signal.values.keys()), 0.5),
    ]

    for kw in keywords:
        if len(kw) < 2:
            continue
        kw_low = kw.lower()
        for field_val, weight in search_fields:
            if kw_low in field_val.lower():
                score += weight

    return score


def _expand_keywords(semantics: NormalizedCaseSemantics) -> List[str]:
    """Expand keywords using synonym dicts."""
    base_kws = _keywords_from_text(semantics.normalized_text or semantics.original_text)

    # Add expanded step keywords
    for step in semantics.expanded_steps:
        base_kws.extend(_keywords_from_text(step))

    # Position expansion
    for pos in semantics.positions:
        for alias_list in POSITION_ALIASES.values():
            if pos in alias_list:
                base_kws.extend(alias_list)

    # Enum value expansions
    for orig, canonical in semantics.enum_value_semantics.items():
        base_kws.append(canonical)
        # Add numeric equivalents
        for pattern, can, num_val in ENUM_LEVEL_PATTERNS:
            if can == canonical and num_val:
                base_kws.append(num_val)

    # Action synonyms
    if semantics.action == "打开":
        base_kws.extend(ACTION_OPEN + ["on", "ON", "1"])
    elif semantics.action == "关闭":
        base_kws.extend(ACTION_CLOSE + ["off", "OFF", "0"])

    return list(set(kw for kw in base_kws if kw and len(kw) >= 2))


def retrieve_candidates(
    semantics: NormalizedCaseSemantics,
    flat_signals: List[FlatSignal],
    top_n: int = TOP_N,
) -> List[Tuple[FlatSignal, float, List[str]]]:
    """
    Returns list of (signal, score, hit_reasons).
    """
    keywords = _expand_keywords(semantics)
    scored = []

    for sig in flat_signals:
        score = _score_signal(sig, keywords)
        if score > 0:
            # Build hit reasons
            reasons = []
            for kw in keywords:
                kw_low = kw.lower()
                if kw_low in (sig.signal_name or "").lower():
                    reasons.append(f"signal_name:{kw}")
                elif kw_low in (sig.signal_desc or "").lower():
                    reasons.append(f"signal_desc:{kw}")
                elif kw_low in (sig.message_name or "").lower():
                    reasons.append(f"message_name:{kw}")
                elif kw_low in " ".join(sig.values.values()).lower():
                    reasons.append(f"enum_value:{kw}")
            scored.append((sig, score, reasons[:5]))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]
