from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

CANONICAL_FIELDS = {
    "company_name",
    "capital",
    "address",
    "corporate_purpose",
    "duration",
    "manager",
    "president_directeur_general",
    "president",
    "directeur_general",
    "auditor",
}

KEY_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "company_name": [
        re.compile(r"\bd[ée]nomination(?:\s+sociale)?\b", re.IGNORECASE),
        re.compile(r"\braison\s+sociale\b", re.IGNORECASE),
    ],
    "capital": [
        re.compile(r"\bcapital(?:\s+social)?\b", re.IGNORECASE),
        re.compile(r"\bmontant\s+(?:du\s+)?capital\b", re.IGNORECASE),
        re.compile(r"\bmontant\s+souscrit\b", re.IGNORECASE),
    ],
    "address": [
        re.compile(r"\bsi[èe]ge(?:\s+social)?\b", re.IGNORECASE),
        re.compile(r"\badresse\b", re.IGNORECASE),
    ],
    "corporate_purpose": [
        re.compile(r"\bobjet(?:\s+social)?\b", re.IGNORECASE),
        re.compile(r"\braison\s+sociale\b", re.IGNORECASE),
        re.compile(r"\bactivit[ée]\b", re.IGNORECASE),
    ],
    "duration": [
        re.compile(r"\bdur[ée]e(?:\s+de\s+la\s+soci[ée]t[ée])?\b", re.IGNORECASE),
    ],
    "manager": [
        re.compile(r"\bg[ée]rant\b", re.IGNORECASE),
        re.compile(r"\bfondateur\b", re.IGNORECASE),
        re.compile(r"\bpromoteur\b", re.IGNORECASE),
        re.compile(r"\bconseil\s+d['’]administration\b", re.IGNORECASE),
        re.compile(r"\bpremier\s+conseil\s+d['’]administration\b", re.IGNORECASE),
        re.compile(r"\bii\s*conseil\s+d['’]administration\b", re.IGNORECASE),
        re.compile(r"\bpr[ée]sident(?:\s+du\s+conseil)?\b", re.IGNORECASE),
        re.compile(r"\bdirecteur\s+g[ée]n[ée]ral\b", re.IGNORECASE),
        re.compile(r"\bpdg\b", re.IGNORECASE),
        re.compile(r"\bil\s+appert\s+que\b", re.IGNORECASE),
    ],
    "president_directeur_general": [
        re.compile(r"\bpr[ée]sident\s+directeur\s+g[ée]n[ée]ral\b", re.IGNORECASE),
        re.compile(r"\bpdg\b", re.IGNORECASE),
        re.compile(r"\bconseil\s+d['’]administration\b", re.IGNORECASE),
    ],
    "president": [
        re.compile(r"\bpr[ée]sident(?:\s+du\s+conseil)?\b", re.IGNORECASE),
        re.compile(r"\bconseil\s+d['’]administration\b", re.IGNORECASE),
    ],
    "directeur_general": [
        re.compile(r"\bdirecteur\s+g[ée]n[ée]ral\b", re.IGNORECASE),
        re.compile(r"\bconseil\s+d['’]administration\b", re.IGNORECASE),
    ],
    "auditor": [
        re.compile(r"\bcommissaire\s+aux\s+comptes\b", re.IGNORECASE),
    ],
}

BAD_VALUE_PATTERNS = [
    re.compile(r"\bconstitution\s+de\s+soci[ée]t[ée]s\b", re.IGNORECASE),
    re.compile(r"\bextraits?\s+des\b", re.IGNORECASE),
    re.compile(r"\b(?:i|ii|iii|iv|v)\s*[-–]\b", re.IGNORECASE),
]


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _norm_text(value: str) -> str:
    value = _strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _clean_value(value: str) -> Optional[str]:
    cleaned = re.sub(r"\s+", " ", value).strip(" \t\n\r,;:-")
    if not cleaned:
        return None
    return cleaned


ROLE_VALUE_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "president_directeur_general": [
        re.compile(
            r"(?:-|\*|•)\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*pr[ée]sident\s*[-\s]*directeur\s*[-\s]*g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+nomm[ée]\s+pr[ée]sident\s+directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"pr[ée]sident\s+directeur\s+g[ée]n[ée]ral[^\n,:;]*[:,-]?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})",
            re.IGNORECASE,
        ),
    ],
    "president": [
        re.compile(
            r"(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+et\s+(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}\s+ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:-|\*|•)\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+nomm[ée]\s+pr[ée]sident(?:\s+du\s+conseil)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"pr[ée]sident(?:\s+du\s+conseil)?[^\n,:;]*[:,-]?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})",
            re.IGNORECASE,
        ),
    ],
    "directeur_general": [
        re.compile(
            r"(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}\s+et\s+(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:-|\*|•)\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*directeur\s+g[ée]n[ée]ral(?:\s+adjoint)?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+nomm[ée]\s+directeur\s+g[ée]n[ée]ral",
            re.IGNORECASE,
        ),
        re.compile(
            r"directeur\s+g[ée]n[ée]ral[^\n,:;]*[:,-]?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})",
            re.IGNORECASE,
        ),
    ],
    "auditor": [
        re.compile(
            r"commissaire\s+aux\s+comptes[^\n,:;]*[:,-]?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame|Bureau|Cabinet)\s+[^\.\n]{2,180})",
            re.IGNORECASE,
        )
    ],
    "manager": [
        re.compile(
            r"(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}\s+et\s+(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*(?:pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+directeur\s+g[ée]n[ée]ral|pr[ée]sident\s+directeur\s+g[ée]n[ée]ral\s+et\s+directeur\s+g[ée]n[ée]ral\s+adjoint)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:-|\*|•)\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*(?:pr[ée]sident(?:\s*[-\s]*directeur\s*[-\s]*g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral(?:\s+adjoint)?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?(?:pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|pr[ée]sident(?:\s+du\s+conseil)?|directeur\s+g[ée]n[ée]ral|g[ée]rant|PDG)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+(?:pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|pr[ée]sident(?:\s+du\s+conseil)?|directeur\s+g[ée]n[ée]ral|g[ée]rant|PDG)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+nomm[ée]\s+(?:pr[ée]sident(?:\s+directeur\s+g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral|g[ée]rant)",
            re.IGNORECASE,
        ),
        re.compile(
            r"nomination\s+de\s+(?P<name>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+en\s+tant\s+que\s+(?:pr[ée]sident(?:\s+directeur\s+g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral|g[ée]rant)",
            re.IGNORECASE,
        ),
    ],
}


def _extract_role_value(field: str, value: str) -> Optional[str]:
    patterns = ROLE_VALUE_PATTERNS.get(field, [])
    for pattern in patterns:
        match = pattern.search(value)
        if match:
            extracted = _clean_value(match.group("name"))
            if extracted:
                return extracted
    return None


def _prepare_candidate(field: str, raw_value: str) -> Optional[str]:
    cleaned = _clean_value(raw_value)
    if cleaned is None:
        return None

    if field in {"manager", "president_directeur_general", "president", "directeur_general", "auditor"}:
        extracted = _extract_role_value(field, cleaned)
        if extracted:
            return extracted

    return cleaned


def _iter_pairs(node: Any, parent_key: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).startswith("_"):
                continue

            merged_key = f"{parent_key} {key}".strip()
            if isinstance(value, str):
                yield merged_key, value
            elif isinstance(value, (int, float)):
                yield merged_key, str(value)
            else:
                yield from _iter_pairs(value, merged_key)
    elif isinstance(node, list):
        str_items = [item.strip() for item in node if isinstance(item, str) and item.strip()]
        if str_items:
            yield parent_key, " ".join(str_items)

        for item in node:
            if isinstance(item, (dict, list)):
                yield from _iter_pairs(item, parent_key)


def _field_from_key(key: str) -> Optional[str]:
    key_norm = _norm_text(key)
    if not key_norm:
        return None

    for field, patterns in KEY_PATTERNS.items():
        if any(pattern.search(key_norm) for pattern in patterns):
            return field
    return None


def _guess_fields_from_value(value: str) -> List[str]:
    guessed: List[str] = []
    lower = value.lower()

    if re.search(r"\bpr[ée]sident\s+directeur\s+g[ée]n[ée]ral\b|\bpdg\b", lower, re.IGNORECASE):
        guessed.append("president_directeur_general")
        guessed.append("manager")
    if re.search(r"\bpr[ée]sident(?:\s+du\s+conseil)?\b", lower, re.IGNORECASE):
        guessed.append("president")
        guessed.append("manager")
    if re.search(r"\bdirecteur\s+g[ée]n[ée]ral\b", lower, re.IGNORECASE):
        guessed.append("directeur_general")
        guessed.append("manager")
    if re.search(r"\bcommissaire\s+aux\s+comptes\b", lower, re.IGNORECASE):
        guessed.append("auditor")

    deduped: List[str] = []
    for field in guessed:
        if field not in deduped:
            deduped.append(field)
    return deduped


def _looks_like_noise(value: str) -> bool:
    return any(pattern.search(value) for pattern in BAD_VALUE_PATTERNS)


def _candidate_in_text(candidate: str, notice_text: str) -> bool:
    cand_norm = _norm_text(candidate)
    text_norm = _norm_text(notice_text)
    if not cand_norm or not text_norm:
        return False

    if len(cand_norm) >= 12 and cand_norm in text_norm:
        return True

    tokens = [tok for tok in cand_norm.split() if len(tok) >= 4]
    if not tokens:
        return False

    hits = sum(1 for token in tokens if token in text_norm)
    required = min(3, max(1, len(tokens) // 2))
    return hits >= required


def _valid_for_field(field: str, value: str) -> bool:
    if len(value) < 3 or len(value) > 500:
        return False
    if _looks_like_noise(value):
        return False

    if field == "company_name" and len(value) > 160:
        return False
    if field == "manager":
        if len(value) > 220:
            return False
        if not re.search(
            r"\b(M\.?|Mr\.?|Mme|Mlle|Monsieur|Madame|g[ée]rant|pr[ée]sident|directeur\s+g[ée]n[ée]ral|fondateur|promoteur)\b",
            value,
            re.IGNORECASE,
        ):
            return False
    if field == "capital" and not re.search(r"\b(dt|dinar|dollars?|euro|€)\b|\d", value, re.IGNORECASE):
        return False
    if field == "duration" and not re.search(r"\b(an|ans|ann[ée]e|ann[ée]es|mois)\b|\d", value, re.IGNORECASE):
        return False

    return True


def load_friend_index(friend_data_dir: Path) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}

    if not friend_data_dir.exists():
        return index

    for path in sorted(friend_data_dir.rglob("*.json")):
        if not path.is_file():
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        ref = payload.get("_reference")
        if not isinstance(ref, str) or not ref.strip():
            ref = path.stem
        ref = ref.strip()

        candidates: Dict[str, str] = {}
        for key, raw_value in _iter_pairs(payload):
            fields: List[str] = []

            key_field = _field_from_key(key)
            if key_field is not None and key_field in CANONICAL_FIELDS:
                fields.append(key_field)

            for guessed_field in _guess_fields_from_value(raw_value):
                if guessed_field in CANONICAL_FIELDS and guessed_field not in fields:
                    fields.append(guessed_field)

            if not fields:
                continue

            for field in fields:
                value = _prepare_candidate(field, raw_value)
                if value is None or not _valid_for_field(field, value):
                    continue

                previous = candidates.get(field)
                if previous is None or len(value) < len(previous):
                    candidates[field] = value

        if candidates:
            index[ref] = candidates

    return index


def apply_friend_fallback(
    record: Dict[str, object],
    notice_text: str,
    reference: str,
    friend_index: Dict[str, Dict[str, str]],
) -> int:
    friend_fields = friend_index.get(reference)
    if not friend_fields:
        return 0

    updated = 0
    for field, candidate in friend_fields.items():
        if record.get(field) is not None:
            continue
        if not _candidate_in_text(candidate, notice_text):
            continue

        record[field] = candidate
        updated += 1

    return updated
