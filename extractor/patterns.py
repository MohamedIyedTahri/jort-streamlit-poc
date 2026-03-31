from __future__ import annotations

import re
from typing import Dict, List

REGEX_FLAGS = re.IGNORECASE | re.DOTALL
SEPARATOR = r"\s*(?::|=)\s*"

LABEL_TOKENS = [
    r"D[ée]nomination(?:\s+sociale)?(?:\s+de\s+la\s+soci[ée]t[ée])?",
    r"Raison\s+sociale",
    r"Forme(?:\s+de\s+la\s+soci[ée]t[ée])?|Forme\s+juridique|Type(?:\s+de\s+la\s+soci[ée]t[ée])?",
    r"Si[èe]ge(?:\s+social)?|Adresse",
    r"Capital(?:\s+social)?|Montant\s+du\s+capital(?:\s+social)?(?:\s+[àa]\s+souscrire)?",
    r"Objet(?:\s+social)?|Activit[ée]",
    r"Dur[ée]e(?:\s+de\s+la\s+soci[ée]t[ée])?|La\s+dur[ée]e\s+pr[ée]vue\s+de\s+la\s+soci[ée]t[ée]",
    r"G[ée]rant(?:e|s|e\s+statutaire)?",
    r"G[ée]rance",
    r"Fondateur",
    r"Pr[ée]sident(?:\s+du\s+conseil)?",
    r"Directeur\s+g[ée]n[ée]ral",
    r"Administrateur(?:s)?",
]
STOP_LABELS = "|".join(LABEL_TOKENS)
LOOSE_STOP_LABELS = "|".join(
    [
        r"D[ée]nomination(?:\s+sociale)?(?:\s+de\s+la\s+soci[ée]t[ée])?",
        r"Raison\s+sociale",
        r"Forme(?:\s+de\s+la\s+soci[ée]t[ée])?|Forme\s+juridique|Type(?:\s+de\s+la\s+soci[ée]t[ée])?",
        r"Si[èe]ge(?:\s+social)?|Adresse",
        r"Capital(?:\s+social)?|Montant\s+du\s+capital(?:\s+social)?(?:\s+[àa]\s+souscrire)?",
        r"Dur[ée]e(?:\s+de\s+la\s+soci[ée]t[ée])?|La\s+dur[ée]e\s+pr[ée]vue\s+de\s+la\s+soci[ée]t[ée]",
        r"G[ée]rant(?:e|s|e\s+statutaire)?|G[ée]rance|Fondateur",
        r"Pr[ée]sident(?:\s+du\s+conseil)?|Directeur\s+g[ée]n[ée]ral|Administrateur(?:s)?",
    ]
)


def _field_pattern(label_group: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?:{label_group}){SEPARATOR}(?P<value>.+?)"
        rf"(?=\n\s*(?:{STOP_LABELS}){SEPARATOR}|\n\s*(?:{LOOSE_STOP_LABELS})\b|\n\s*\d+\s*[-–]|\n{{2,}}|$)",
        REGEX_FLAGS,
    )


def _line_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


FIELD_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "company_name": [
        _field_pattern(
            r"D[ée]nomination(?:\s+sociale)?(?:\s+de\s+la\s+soci[ée]t[ée])?|Raison\s+sociale"
        ),
    ],
    "legal_form_text": [
        _field_pattern(
            r"Forme(?:\s+de\s+la\s+soci[ée]t[ée])?|Forme\s+juridique|Type(?:\s+de\s+la\s+soci[ée]t[ée])?"
        ),
    ],
    "address": [
        _field_pattern(r"Si[èe]ge(?:\s+social)?|Adresse"),
    ],
    "capital": [
        _field_pattern(
            r"Montant\s+du\s+capital(?:\s+social)?(?:\s+[àa]\s+souscrire)?|Capital(?:\s+social)?"
        ),
        _line_pattern(r"\bau\s+capital\s+de\b\s*(?P<value>[^\n]+)"),
    ],
    "corporate_purpose": [
        _field_pattern(r"Objet(?:\s+social)?|Activit[ée]|Raison\s+sociale"),
        _line_pattern(
            r"\b(?:ayant\s+pour\s+objet|a\s+pour\s+objet)\s+(?P<value>[^\n]+)"
        ),
        _line_pattern(
            r"\bdont\s+l['’]objet(?:\s+social)?\s+(?:est|consiste\s+en)?\s*(?P<value>[^\n]+)"
        ),
        _line_pattern(
            r"\b(?:son\s+)?objet(?:\s+social)?\s+(?:est|consiste\s+en)\s*(?P<value>[^\n]+)"
        ),
        _line_pattern(
            r"\braison\s+sociale\s*:\s*(?P<value>[^\n]+)"
        ),
    ],
    "duration": [
        _field_pattern(
            r"Dur[ée]e(?:\s+de\s+la\s+soci[ée]t[ée])?|La\s+dur[ée]e\s+pr[ée]vue\s+de\s+la\s+soci[ée]t[ée]"
        ),
        _line_pattern(
            r"\bdur[ée]e\b\s+(?:pr[ée]vue\s+)?(?:de\s+la\s+soci[ée]t[ée]\s+)?(?P<value>[^\n]+)"
        ),
        _line_pattern(
            r"\bpour\s+une\s+dur[ée]e\s+de\s+(?P<value>[^\n\.,;:]{1,80}\s+(?:ans?|ann[ée]es?|mois))"
        ),
        _line_pattern(
            r"\b(?:constitu[ée]e?|cr[ée][ée]e?)\s+pour\s+(?P<value>[^\n\.,;:]{1,80}\s+(?:ans?|ann[ée]es?|mois))"
        ),
        _line_pattern(
            r"\bprorog[ée]e?\s+pour\s+(?P<value>[^\n\.,;:]{1,80}\s+(?:ans?|ann[ée]es?|mois))"
        ),
        _line_pattern(
            r"\bexpire(?:ra)?\s+(?:le\s+jour\s+o[uù]|lors\s+de|[àa]\s+l[’']issue\s+de)\s+(?P<value>[^\n]{1,120})"
        ),
        _line_pattern(
            r"\b(?P<value>(?:\d+|quatre\s+vingt\s+dix\s+neuf|quatre-vingt-dix-neuf|quatre\s+vingt\s+dix|quatre-vingt-dix|cent)\s+(?:ans?|ann[ée]es?|mois))\b"
        ),
    ],
    "manager": [
        _field_pattern(
            r"G[ée]rant(?:e|s|e\s+statutaire)?|G[ée]rance|Fondateur|Pr[ée]sident(?:\s+du\s+conseil)?|Directeur\s+g[ée]n[ée]ral|Administrateur(?:s)?"
        ),
        _line_pattern(
            r"nomination\s+de\s+(?P<value>(?:M\.|Mme|Monsieur|Mlle)\s+[^,\.\n]{2,140})\s+en\s+tant\s+que\s+(?:Pr[ée]sident(?:\s+Directeur\s+G[ée]n[ée]ral)?|Directeur\s+g[ée]n[ée]ral|g[ée]rant)"
        ),
        _line_pattern(
            r"(?:(?:M\.|Mme|Monsieur|Mlle)\s+(?P<value>[^,\.\n]{2,140}))\s+(?:est\s+)?(?:nomm[ée]|d[ée]sign[ée])\s+(?:en\s+tant\s+que|comme)\s+(?:Pr[ée]sident(?:\s+Directeur\s+G[ée]n[ée]ral)?|Directeur\s+g[ée]n[ée]ral|g[ée]rant)"
        ),
    ],
}


ROLE_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "president_directeur_general": [
        _line_pattern(
            r"(?:-|\*|•)\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*Pr[ée]sident\s*[-\s]*Directeur\s*[-\s]*G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?Pr[ée]sident(?:\s*[-\s]\s*|\s+)Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+Pr[ée]sident(?:\s*[-\s]\s*|\s+)Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+d[ée]sign[ée]\s+en\s+qualit[ée]\s+de\s+Pr[ée]sident(?:\s*[-\s]\s*|\s+)Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"nomination\s+du\s+PDG\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+est\s+nomm[ée]\s+PDG"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+est\s+nomm[ée]\s+pr[ée]sident\s+directeur\s+g[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+a\s+[ée]t[ée]\s+nomm[ée]\s+Pr[ée]sident\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:nomination\s+de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+(?:en\s+tant\s+que\s+)?Pr[ée]sident\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"Pr[ée]sident\s+Directeur\s+G[ée]n[ée]ral[^\n,:;]*[:,-]?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})"
        ),
    ],
    "president": [
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+et\s+(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}\s+ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*Pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:-|\*|•)\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*Pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?Pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+Pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+d[ée]sign[ée]\s+en\s+qualit[ée]\s+de\s+Pr[ée]sident(?:\s+du\s+conseil(?:\s+d['’]administration)?)?"
        ),
        _line_pattern(
            r"Nomination\s+de\s+(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+dans\s+les\s+fonctions\s+de\s+Pr[ée]sident(?:\s+du\s+conseil\s+d['’]administration)?"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*[:\-]\s*Pr[ée]sident(?:\s+du\s+conseil)?"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+a\s+[ée]t[ée]\s+nomm[ée]\s+Pr[ée]sident(?:\s+du\s+conseil)?"
        ),
        _line_pattern(
            r"(?:nomination\s+de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+(?:en\s+tant\s+que\s+)?Pr[ée]sident(?:\s+du\s+conseil)?"
        ),
        _line_pattern(
            r"Pr[ée]sident(?:\s+du\s+conseil)?[^\n,:;]*[:,-]?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})"
        ),
    ],
    "directeur_general": [
        _line_pattern(
            r"(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}\s+et\s+(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+ont\s+[ée]t[ée]\s+nomm[ée]s?\s+respectivement\s*,?\s*Pr[ée]sident(?:\s+du\s+conseil)?\s+et\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:-|\*|•)\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^\n,\.]{2,140})\s*,\s*Directeur\s+G[ée]n[ée]ral(?:\s+adjoint)?"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nomination\s+de)\s*(?:de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*(?:en\s+qualit[ée]\s+de\s+)?Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée])\s*[:\-]?\s*(?:\*|-)?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*,?\s*en\s+qualit[ée]\s+de\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+a\s+[ée]t[ée]\s+d[ée]sign[ée]\s+en\s+qualit[ée]\s+de\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"Nomination\s+de\s+(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s+dans\s+les\s+fonctions\s+de\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})\s*[:\-]\s*Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"Pr[ée]sident[^\n]{0,160}?et\s+directeur\s+g[ée]n[ée]ral[^\n]{0,80}?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+a\s+[ée]t[ée]\s+nomm[ée]\s+Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"(?:nomination\s+de\s+)?(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140}?)\s+(?:en\s+tant\s+que\s+)?Directeur\s+G[ée]n[ée]ral"
        ),
        _line_pattern(
            r"Directeur\s+G[ée]n[ée]ral[^\n,:;]*[:,-]?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame)\s+[^,\.\n]{2,140})"
        ),
    ],
    "administrators": [
        _line_pattern(
            r"administrateurs?[^\n:]*[:,-]\s*(?P<value>(?:Messieurs?|M\.|Mme|Mlle|Monsieur|Madame)[^\n]+)"
        ),
    ],
    "auditor": [
        _line_pattern(
            r"commissaire\s+aux\s+comptes[^\n:]*[:,-]?\s*(?P<value>(?:M\.|Mr\.?|Mme|Mlle|Monsieur|Madame|Bureau)\s+[^\n\.]{2,200})"
        ),
    ],
}
