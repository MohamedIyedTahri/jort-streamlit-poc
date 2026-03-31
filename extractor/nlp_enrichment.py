from __future__ import annotations

import re
from typing import Dict, List, Optional

import spacy

_NLP = None


PERSON_TITLE_RE = re.compile(r"^(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+", re.IGNORECASE)
PERSON_NAME_RE = re.compile(
    r"\b(?P<name>[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'\-]+(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'\-]+){1,4})\b"
)

ROLE_PATTERNS = {
    "president_directeur_general": re.compile(r"pr[ée]sident\s*[-\s]*direct\w*\s+g[ée]n[ée]ral|\bpdg\b", re.IGNORECASE),
    "president": re.compile(r"pr[ée]sident(?:\s+du\s+conseil)?", re.IGNORECASE),
    "directeur_general": re.compile(r"directeur\s+g[ée]n[ée]ral", re.IGNORECASE),
    "manager": re.compile(r"pr[ée]sident|directeur\s+g[ée]n[ée]ral|\bpdg\b|g[ée]rant", re.IGNORECASE),
}

NOMINATION_LEMMAS = {"nommer", "designer", "élire", "elire", "désigner"}

CORE_LABEL_PATTERNS = {
    "company_name": re.compile(r"d[ée]nomination|raison\s+sociale", re.IGNORECASE),
    "address": re.compile(r"si[èe]ge\s+social|si[èe]ge|adresse", re.IGNORECASE),
    "capital": re.compile(r"capital|montant\s+du\s+capital|au\s+capital\s+de", re.IGNORECASE),
    "corporate_purpose": re.compile(r"objet\s+social|objet|activit[ée]", re.IGNORECASE),
    "duration": re.compile(r"dur[ée]e", re.IGNORECASE),
}

STOP_LABEL_RE = re.compile(
    r"d[ée]nomination|raison\s+sociale|si[èe]ge|adresse|capital|objet|activit[ée]|dur[ée]e|g[ée]rant|pr[ée]sident|directeur\s+g[ée]n[ée]ral",
    re.IGNORECASE,
)


def _get_nlp():
    global _NLP
    if _NLP is not None:
        return _NLP

    try:
        _NLP = spacy.load("fr_core_news_sm")
    except Exception:
        _NLP = spacy.blank("fr")
        if "sentencizer" not in _NLP.pipe_names:
            _NLP.add_pipe("sentencizer")

    return _NLP


def _is_person_like(candidate: str) -> bool:
    low = candidate.lower().strip()
    if len(low) < 5:
        return False

    noisy_words = [
        "soci",
        "cabinet",
        "sicar",
        "banque",
        "holding",
        "audit",
        "ago",
        "assembl",
        "statut",
        "depot",
        "dépot",
    ]
    if any(token in low for token in noisy_words):
        return False

    if any(low.startswith(prefix) for prefix in ["trois ans", "deux ans", "un an", "la durée", "durée"]):
        return False

    if re.search(r"\b(exercice|mandat|pouvoirs?)\b", low):
        return False

    # Avoid capturing a single token or long narrative fragments.
    tokens = [tok for tok in re.split(r"\s+", candidate) if tok]
    if len(tokens) < 2:
        return False
    if len(tokens) > 8:
        return False

    return True


def _clean_person(candidate: str) -> Optional[str]:
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,.;:-")
    candidate = re.sub(r"^\d+\s*[-.)]\s*", "", candidate)

    # Trim common appositions that are not part of the name.
    candidate = re.split(
        r",\s*(?:tunisien(?:ne)?|demeurant|domicili[ée]|[ée]lisant\s+domicile|de\s+nationalit[ée]|titulaire)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()

    candidate = PERSON_TITLE_RE.sub("", candidate).strip()
    if not _is_person_like(candidate):
        return None
    return candidate


def _extract_person_ner(sent_doc) -> Optional[str]:
    for ent in sent_doc.ents:
        if ent.label_.upper() in {"PER", "PERSON"}:
            person = _clean_person(ent.text)
            if person:
                return person
    return None


def _extract_person_regex(sentence: str) -> Optional[str]:
    # Prefer a person before a role marker.
    role_match = re.search(r"pr[ée]sident|directeur\s+g[ée]n[ée]ral|\bpdg\b|g[ée]rant", sentence, re.IGNORECASE)
    if role_match:
        left = sentence[: role_match.start()]
        matches = list(PERSON_NAME_RE.finditer(left))
        if matches:
            person = _clean_person(matches[-1].group("name"))
            if person:
                return person

    # Generic backup.
    generic = None
    if re.search(r"nomm|d[ée]sign|[ée]lu|pdg|pr[ée]sident|directeur\s+g[ée]n[ée]ral|g[ée]rant", sentence, re.IGNORECASE):
        generic = PERSON_NAME_RE.search(sentence)
    if generic:
        return _clean_person(generic.group("name"))

    return None


def _indentation_sections(text: str) -> List[str]:
    lines = text.splitlines()
    sections: List[str] = []

    current: List[str] = []
    in_governance = False
    for line in lines:
        raw = line.rstrip()
        if not raw.strip():
            continue

        normalized = re.sub(r"\s+", " ", raw).strip()
        if re.search(r"conseil\s+d['’]administration|premier\s+conseil", normalized, re.IGNORECASE):
            if current:
                sections.append("\n".join(current))
                current = []
            in_governance = True
            current.append(normalized)
            continue

        # Stop when another numbered major section starts.
        if in_governance and re.match(r"^(?:[IVX]+|\d+)\s*[-/).:]", normalized):
            sections.append("\n".join(current))
            current = []
            in_governance = False

        if not in_governance:
            continue

        # Indentation-inspired capture: bullets and list-like lines are prioritized.
        if re.match(r"^\s*(?:[-*•]|\d+[).:-])\s*", raw) or raw.startswith(" "):
            current.append(normalized)
        else:
            current.append(normalized)

    if current:
        sections.append("\n".join(current))

    return sections


def _iter_candidate_lines(text: str) -> List[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


def _extract_after_label(line: str) -> Optional[str]:
    match = re.search(r"[:=]\s*(.+)$", line)
    if match:
        value = match.group(1).strip(" ,.;:-")
        return value or None
    return None


def _first_sentence_chunk(value: str, max_len: int = 260) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = value[:max_len]
    value = re.split(r"\s+(?:II|III|IV|V)\s*[-:/]", value, maxsplit=1)[0].strip()
    return value.strip(" ,;:-")


def extract_core_fields_with_nlp(text: str) -> Dict[str, Optional[str]]:
    nlp = _get_nlp()
    lines = _iter_candidate_lines(text)

    result: Dict[str, Optional[str]] = {
        "company_name": None,
        "address": None,
        "capital": None,
        "corporate_purpose": None,
        "duration": None,
    }

    for idx, line in enumerate(lines):
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        merged = f"{line} {next_line}".strip()

        if result["company_name"] is None and CORE_LABEL_PATTERNS["company_name"].search(line):
            candidate = _extract_after_label(line) or _extract_after_label(merged)
            if candidate is None and next_line and not STOP_LABEL_RE.search(next_line):
                candidate = next_line

            if candidate:
                doc = nlp(candidate)
                org = next((ent.text for ent in doc.ents if ent.label_.upper() in {"ORG", "MISC"}), None)
                picked = org or candidate
                picked = _first_sentence_chunk(picked, max_len=180)
                if len(picked) >= 3:
                    result["company_name"] = picked

        if result["address"] is None and CORE_LABEL_PATTERNS["address"].search(line):
            candidate = _extract_after_label(line) or _extract_after_label(merged)
            if candidate is None and next_line and not STOP_LABEL_RE.search(next_line):
                candidate = next_line
            if candidate:
                picked = _first_sentence_chunk(candidate, max_len=220)
                if len(picked) >= 6:
                    result["address"] = picked

        if result["capital"] is None and CORE_LABEL_PATTERNS["capital"].search(line):
            cap_match = re.search(
                r"((?:\d[\d\s\.,]*)\s*(?:DT|D\.?T\.?|dinars?|dinars\s+tunisiens|euros?|dollars?))",
                merged,
                re.IGNORECASE,
            )
            if cap_match:
                result["capital"] = _first_sentence_chunk(cap_match.group(1), max_len=140)
            else:
                candidate = _extract_after_label(line) or _extract_after_label(merged)
                if candidate:
                    candidate = _first_sentence_chunk(candidate, max_len=160)
                    if re.search(r"\d", candidate):
                        result["capital"] = candidate

        if result["duration"] is None and CORE_LABEL_PATTERNS["duration"].search(line):
            dur_match = re.search(r"((?:\d+|\w+)\s+(?:ans?|ann[ée]es?|mois))", merged, re.IGNORECASE)
            if dur_match:
                result["duration"] = _first_sentence_chunk(dur_match.group(1), max_len=120)
            else:
                candidate = _extract_after_label(line) or _extract_after_label(merged)
                if candidate:
                    candidate = _first_sentence_chunk(candidate, max_len=120)
                    if re.search(r"ans?|ann[ée]es?|mois", candidate, re.IGNORECASE):
                        result["duration"] = candidate

        if result["corporate_purpose"] is None and CORE_LABEL_PATTERNS["corporate_purpose"].search(line):
            candidate = _extract_after_label(line) or _extract_after_label(merged)
            if candidate is None and next_line and not STOP_LABEL_RE.search(next_line):
                candidate = next_line
            if candidate:
                picked = _first_sentence_chunk(candidate, max_len=320)
                if len(picked) >= 10:
                    result["corporate_purpose"] = picked

    if result["corporate_purpose"] is None:
        normalized_text = re.sub(r"\s+", " ", text)
        purpose_patterns = [
            re.compile(
                r"\b(?:ayant\s+pour\s+objet|a\s+pour\s+objet)\s+(?P<value>.+?)(?=\s*(?:,|;|\.)\s*(?:si[èe]ge|capital|dur[ée]e|g[ée]rant|g[ée]rance)\b|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bdont\s+l['’]objet(?:\s+social)?\s+(?:est|consiste\s+en)?\s*(?P<value>.+?)(?=\s*(?:,|;|\.)\s*(?:si[èe]ge|capital|dur[ée]e|g[ée]rant|g[ée]rance)\b|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:son\s+)?objet(?:\s+social)?\s+(?:est|consiste\s+en)\s*(?P<value>.+?)(?=\s*(?:,|;|\.)\s*(?:si[èe]ge|capital|dur[ée]e|g[ée]rant|g[ée]rance)\b|$)",
                re.IGNORECASE,
            ),
        ]
        for pattern in purpose_patterns:
            match = pattern.search(normalized_text)
            if match:
                picked = _first_sentence_chunk(match.group("value"), max_len=320)
                if len(picked) >= 10:
                    result["corporate_purpose"] = picked
                    break

    if result["duration"] is None:
        normalized_text = re.sub(r"\s+", " ", text)
        duration_patterns = [
            re.compile(r"\bpour\s+une\s+dur[ée]e\s+de\s+((?:\d+|[a-zA-ZÀ-ÖØ-öø-ÿ\-]+)\s+(?:ans?|ann[ée]es?|mois))", re.IGNORECASE),
            re.compile(r"\b(?:constitu[ée]e?|cr[ée][ée]e?)\s+pour\s+((?:\d+|[a-zA-ZÀ-ÖØ-öø-ÿ\-]+)\s+(?:ans?|ann[ée]es?|mois))", re.IGNORECASE),
            re.compile(r"\b((?:\d+|[a-zA-ZÀ-ÖØ-öø-ÿ\-]+)\s+(?:ans?|ann[ée]es?|mois))\b", re.IGNORECASE),
        ]
        for pattern in duration_patterns:
            match = pattern.search(normalized_text)
            if match:
                result["duration"] = _first_sentence_chunk(match.group(1), max_len=120)
                break

    return result


def extract_leadership_with_nlp(text: str) -> Dict[str, Optional[str]]:
    nlp = _get_nlp()

    result: Dict[str, Optional[str]] = {
        "manager": None,
        "president_directeur_general": None,
        "president": None,
        "directeur_general": None,
    }

    candidates = _indentation_sections(text)
    candidates.append(text)

    for block in candidates:
        doc = nlp(block)
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue

            sent_low = sent_text.lower()
            sent_lemmas = {token.lemma_.lower() for token in sent if token.lemma_}
            has_nomination = bool(NOMINATION_LEMMAS & sent_lemmas) or any(
                stem in sent_low for stem in ["nomm", "d\u00e9sign", "\u00e9lu", "elu"]
            )
            if not has_nomination and not ROLE_PATTERNS["manager"].search(sent_text):
                continue

            person = _extract_person_ner(sent)
            if person is None:
                person = _extract_person_regex(sent_text)
            if person is None:
                continue

            if ROLE_PATTERNS["president_directeur_general"].search(sent_text):
                result["president_directeur_general"] = result["president_directeur_general"] or person
                result["manager"] = result["manager"] or person
                continue

            if ROLE_PATTERNS["directeur_general"].search(sent_text):
                result["directeur_general"] = result["directeur_general"] or person
                result["manager"] = result["manager"] or person
                continue

            if ROLE_PATTERNS["president"].search(sent_text):
                result["president"] = result["president"] or person
                result["manager"] = result["manager"] or person
                continue

    return result
