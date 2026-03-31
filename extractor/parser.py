from __future__ import annotations

import re
from typing import Dict, Iterable, Optional, Set

from extractor.nlp_enrichment import extract_core_fields_with_nlp, extract_leadership_with_nlp
from extractor.patterns import FIELD_PATTERNS, ROLE_PATTERNS


MANAGER_FALLBACK_PATTERNS = [
    re.compile(
        r"(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140}\s+et\s+"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})\s+"
        r"ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*"
        r"(?:pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+directeur\s+g[ée]n[ée]ral|pr[ée]sident\s+directeur\s+g[ée]n[ée]ral\s+et\s+directeur\s+g[ée]n[ée]ral\s+adjoint)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:-|\*|•)\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})\s*,\s*"
        r"(?:pr[ée]sident(?:\s*[-\s]*directeur\s*[-\s]*g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral(?:\s+adjoint)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})"
        r"\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?"
        r"(?:pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?|directeur\s+g[ée]n[ée]ral|PDG|g[ée]rant)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})"
        r"\s*,?\s*en\s+qualit[ée]\s+de\s+"
        r"(?:pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?|directeur\s+g[ée]n[ée]ral|PDG)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})"
        r"\s+a\s+[ée]t[ée]\s+d[ée]sign[ée]\s+en\s+qualit[ée]\s+de\s+"
        r"(?:pr[ée]sident(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?|directeur\s+g[ée]n[ée]ral|PDG)",
        re.IGNORECASE,
    ),
    re.compile(
        r"nomination\s+du\s+PDG\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})\s+est\s+nomm[ée]\s+PDG",
        re.IGNORECASE,
    ),
    re.compile(
        r"nomm[ée]\s+le\s+pr[ée]sident\s+directeur\s+g[ée]n[ée]ral"
        r"(?:\s+de\s+la\s+soci[ée]t[ée])?,\s*"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})",
        re.IGNORECASE,
    ),
    re.compile(
        r"pr[ée]sident\s+directeur\s+g[ée]n[ée]ral"
        r"(?:\s+de\s+la\s+soci[ée]t[ée])?,\s*"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})",
        re.IGNORECASE,
    ),
    re.compile(
        r"nomination\s+de\s+"
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})"
        r"\s+en\s+tant\s+que\s+"
        r"(?:pr[ée]sident(?:\s+directeur\s+g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral|g[ée]rant)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})"
        r"\s+(?:est\s+)?(?:nomm[ée]|d[ée]sign[ée])"
        r"(?:\s+en\s+tant\s+que|\s+comme)?\s+"
        r"(?:pr[ée]sident(?:\s+directeur\s+g[ée]n[ée]ral)?|directeur\s+g[ée]n[ée]ral|g[ée]rant)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})\s*[:\-]\s*"
        r"(?:pr[ée]sident(?:\s+directeur\s+g[ée]n[ée]ral)?|PDG|directeur\s+g[ée]n[ée]ral)",
        re.IGNORECASE,
    ),
    re.compile(
        r"Nomination\s+de\s+(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n\.,;]{2,140})\s+"
        r"dans\s+les\s+fonctions\s+de\s+(?:Pr[ée]sident(?:\s+du\s+conseil\s+d['’]administration)?|Directeur\s+G[ée]n[ée]ral)",
        re.IGNORECASE,
    ),
]


def _extract_first(patterns: Iterable[re.Pattern[str]], text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group("value")
    return None


def _normalize_text_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return None
    return normalized


def _normalize_person_value(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text_value(value)
    if normalized is None:
        return None

    normalized = re.sub(
        r"\s+(?:en\s+tant\s+que|en\s+qualit[ée]\s+de|tout\s+en|pour\s+la\s+dur[ée]e).*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip(" ,.;:-")

    # Drop obvious non-name fragments.
    if re.search(r"\b(tout\s+en|pouvoirs|nomination|qualit[ée])\b", normalized, re.IGNORECASE):
        return None
    if len(normalized) < 4:
        return None
    return normalized


def _sanitize_leadership_person(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_person_value(value)
    if normalized is None:
        return None

    # Remove frequent appositions that follow a person mention.
    normalized = re.split(
        r",\s*(?:tunisien(?:ne)?|demeurant|domicili[ée]|[ée]lisant\s+domicile|de\s+nationalit[ée]|titulaire)\b",
        normalized,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.;:-")

    lower = normalized.lower()
    if re.search(r"\d", normalized):
        return None

    noisy_tokens = [
        "soci",
        "cabinet",
        "sicar",
        "banque",
        "holding",
        "assembl",
        "conseil",
        "statut",
        "dépôt",
        "depot",
        "capital",
        "commissaire",
        "exercice",
        "mandat",
    ]
    if any(token in lower for token in noisy_tokens):
        return None

    # Multi-person captures are too ambiguous for the single manager field.
    if re.search(r"\s+et\s+", lower):
        return None

    tokens = [tok for tok in re.split(r"\s+", normalized) if tok]
    if len(tokens) < 2 or len(tokens) > 8:
        return None

    return normalized


def _normalize_capital(value: Optional[str]) -> Optional[str]:
    return _normalize_text_value(value)


def _normalize_duration(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text_value(value)
    if normalized is None:
        return None

    normalized = re.split(r"\s+(?:II|III|IV|V)\s*[-:/]", normalized, maxsplit=1, flags=re.IGNORECASE)[0]
    normalized = re.split(
        r"\s+(?:d[ée]claration|assembl[ée]e|conseil|d[ée]p[ôo]t|publicit[ée]|statuts?)\b",
        normalized,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.;:-")

    if len(normalized) > 140:
        match = re.search(r"((?:\d+|[a-zA-ZÀ-ÖØ-öø-ÿ\-]+)\s+(?:ans?|ann[ée]es?|mois))", normalized, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    return normalized if normalized else None


def _normalize_corporate_purpose(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text_value(value)
    if normalized is None:
        return None

    trimmed = re.split(
        r"\s*(?:,|;|\.|\|)\s*(?:son\s+si[èe]ge|si[èe]ge\s+social|capital|dur[ée]e|g[ée]rance|g[ée]rant|d[ée]nomination|d[ée]p[ôo]t|registre|matricule|publicit[ée])\b",
        normalized,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.;:-")

    # Keep the original value when trimming becomes too aggressive.
    if len(trimmed) >= 12:
        normalized = trimmed

    if len(normalized) > 420:
        normalized = normalized[:420].rstrip(" ,.;:-")

    return normalized if len(normalized) >= 5 else None


def _company_name_fallback(text: str) -> Optional[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines[:40]):
        if re.search(r"Constitution|Cr[ée]ation|Notice", line, re.IGNORECASE):
            for candidate in lines[index + 1 : index + 8]:
                if ":" in candidate:
                    continue
                if 3 <= len(candidate) <= 180:
                    return _normalize_text_value(candidate)

    return None


def _manager_sentence_fallback(text: str) -> Optional[str]:
    for pattern in MANAGER_FALLBACK_PATTERNS:
        match = pattern.search(text)
        if match:
            return _normalize_text_value(match.group("value"))
    return None


def _extract_role(role_key: str, text: str) -> Optional[str]:
    value = _extract_first(ROLE_PATTERNS.get(role_key, []), text)
    if role_key in {"president_directeur_general", "president", "directeur_general", "auditor"}:
        return _normalize_person_value(value)
    return _normalize_text_value(value)


def _has_label_or_keyword(text: str, patterns: Iterable[str]) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower, re.IGNORECASE) for pattern in patterns)


def _resolve_not_applicable_fields(
    legal_form: str,
    text: str,
    manager: Optional[str],
    capital: Optional[str],
    duration: Optional[str],
) -> Set[str]:
    not_applicable: Set[str] = set()

    if legal_form == "anonyme" and manager is None:
        has_leadership_signal = _has_label_or_keyword(
            text,
            [
                r"g[ée]rant",
                r"pr[ée]sident",
                r"directeur\s+g[ée]n[ée]ral",
                r"administrateurs?",
            ],
        )
        if not has_leadership_signal:
            not_applicable.add("manager")

    if legal_form == "autre":
        if manager is None and not _has_label_or_keyword(text, [r"g[ée]rant", r"fondateur", r"pr[ée]sident"]):
            not_applicable.add("manager")
        if capital is None and not _has_label_or_keyword(text, [r"capital", r"au\s+capital\s+de"]):
            not_applicable.add("capital")
        if duration is None and not _has_label_or_keyword(text, [r"dur[ée]e", r"ann?[ée]es?", r"ans?"]):
            not_applicable.add("duration")

    return not_applicable


def is_constitution_notice(text: str) -> bool:
    lower = text.lower()

    positive_markers = [
        r"\bconstitution\b",
        r"\bcr[ée]ation\b",
        r"notice\s+au\s+public",
        r"assembl[ée]e\s+g[ée]n[ée]rale\s+constitutive",
    ]
    negative_markers = [
        r"convocation\s+[àa]\s+l[’']assembl[ée]e\s+g[ée]n[ée]rale",
        r"\bordre\s+du\s+jour\b",
        r"avis\s+de\s+convocation",
        r"assembl[ée]e\s+g[ée]n[ée]rale\s+ordinaire",
        r"assembl[ée]e\s+g[ée]n[ée]rale\s+extraordinaire",
    ]

    has_positive = any(re.search(pattern, lower, re.IGNORECASE) for pattern in positive_markers)
    has_negative = any(re.search(pattern, lower, re.IGNORECASE) for pattern in negative_markers)

    if has_positive:
        return True
    if has_negative:
        return False

    structural_labels = [
        r"d[ée]nomination",
        r"(si[èe]ge|adresse)",
        r"capital",
        r"(objet|activit[ée]|raison\s+sociale)",
        r"dur[ée]e",
    ]
    score = sum(1 for pattern in structural_labels if re.search(pattern, lower, re.IGNORECASE))
    return score >= 3


def parse_notice(text: str, metadata: Dict[str, object]) -> Dict[str, object]:
    """Extract structured fields from a single cleaned notice text."""
    legal_form = str(metadata.get("legal_form") or "")

    company_name = _normalize_text_value(
        _extract_first(FIELD_PATTERNS["company_name"], text)
    ) or _company_name_fallback(text)
    address = _normalize_text_value(_extract_first(FIELD_PATTERNS["address"], text))
    corporate_purpose = _normalize_text_value(
        _extract_first(FIELD_PATTERNS["corporate_purpose"], text)
    )
    manager_label = _normalize_text_value(_extract_first(FIELD_PATTERNS["manager"], text))
    manager_sentence = _normalize_person_value(_manager_sentence_fallback(text))
    capital = _normalize_capital(_extract_first(FIELD_PATTERNS["capital"], text))
    duration = _normalize_duration(_extract_first(FIELD_PATTERNS["duration"], text))

    # NLP core-field fallback: indentation-aware line scan + lemmatized cues + NER.
    if any(value is None for value in [company_name, address, capital, corporate_purpose, duration]):
        nlp_core = extract_core_fields_with_nlp(text)
        company_name = company_name or _normalize_text_value(nlp_core.get("company_name"))
        address = address or _normalize_text_value(nlp_core.get("address"))
        capital = capital or _normalize_capital(nlp_core.get("capital"))
        if corporate_purpose is None:
            corporate_purpose = _normalize_corporate_purpose(nlp_core.get("corporate_purpose"))
        duration = duration or _normalize_duration(nlp_core.get("duration"))

    president_directeur_general = _extract_role("president_directeur_general", text)
    president = _extract_role("president", text)
    directeur_general = _extract_role("directeur_general", text)
    administrators = _extract_role("administrators", text)
    if administrators and re.search(r"\b(tout\s+en|pouvoirs|nomination)\b", administrators, re.IGNORECASE):
        administrators = None
    auditor = _extract_role("auditor", text)

    # Legal-form-aware manager mapping keeps compatibility with existing schema.
    if legal_form in {"sarl", "suarl"}:
        manager = manager_label or manager_sentence
    elif legal_form == "anonyme":
        manager = (
            _sanitize_leadership_person(manager_label)
            or manager_sentence
            or president_directeur_general
            or directeur_general
            or president
        )

        # NLP fallback (indentation-aware section scan + lemmatization + NER)
        # is applied only when regex extraction still leaves leadership missing.
        if manager is None or (president_directeur_general is None and president is None and directeur_general is None):
            nlp_roles = extract_leadership_with_nlp(text)
            president_directeur_general = president_directeur_general or _sanitize_leadership_person(
                nlp_roles.get("president_directeur_general")
            )
            president = president or _sanitize_leadership_person(nlp_roles.get("president"))
            directeur_general = directeur_general or _sanitize_leadership_person(
                nlp_roles.get("directeur_general")
            )
            manager = manager or _sanitize_leadership_person(nlp_roles.get("manager"))
    else:
        manager = manager_label or manager_sentence

    president_directeur_general = _sanitize_leadership_person(president_directeur_general)
    president = _sanitize_leadership_person(president)
    directeur_general = _sanitize_leadership_person(directeur_general)
    if legal_form == "anonyme":
        manager = _sanitize_leadership_person(manager)

    not_applicable_fields = sorted(
        _resolve_not_applicable_fields(legal_form, text, manager, capital, duration)
    )

    # Path-derived metadata is authoritative for legal form/year/issue/source.
    record: Dict[str, object] = {
        "company_name": company_name,
        "legal_form": metadata.get("legal_form"),
        "capital": capital,
        "address": address,
        "corporate_purpose": corporate_purpose,
        "duration": duration,
        "manager": manager,
        "president_directeur_general": president_directeur_general,
        "president": president,
        "directeur_general": directeur_general,
        "administrators": administrators,
        "auditor": auditor,
        "not_applicable_fields": not_applicable_fields,
        "year": metadata.get("year"),
        "issue_number": metadata.get("issue_number"),
        "source_file": metadata.get("source_file"),
    }

    return record
