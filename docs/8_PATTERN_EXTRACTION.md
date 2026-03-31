# 8. Extraction par Patterns Regex

## FIELD_PATTERNS: Extraction des Champs Principaux

### **Pattern Definition Helper**

```python
import re
from typing import List, Optional

def _field_pattern(
    label_regex: str,
    value_regex: str = r"[^\n]+",
    stop_labels: Optional[List[str]] = None,
    capture_all: bool = False
) -> re.Pattern:
    """
    Build regex for matching 'Label: Value' pairs.
    
    Args:
        label_regex: Regex matching label (e.g., "Dénomination|Raison sociale")
        value_regex: Regex matching value (e.g., r"[A-Z][^\\n]+")
        stop_labels: Labels that signal end of value (e.g., other field labels)
        capture_all: If True, capture multiple lines until stop_label
    
    Returns:
        Compiled regex pattern with 'value' named group
    
    Example:
        _field_pattern(
            r"Dénomination|Raison\s+sociale",
            r"[A-Za-z][^\n]+",
            stop_labels=["Capital", "Adresse"]
        )
        Matches: "Dénomination: MY COMPANY SARL" → group('value') = "MY COMPANY SARL"
    """
    
    # Build base pattern
    pattern = (
        f"(?i)(?:{label_regex})"  # Case-insensitive label
        f"\\s*:?\\s*"              # Optional colon + spacing
        f"(?P<value>{value_regex})"
    )
    
    # Add stop-label lookahead (optional)
    if stop_labels:
        stop_pattern = "|".join(re.escape(label) for label in stop_labels)
        pattern += f"(?=\\n(?:{stop_pattern}))"
    
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)
```

### **All FIELD_PATTERNS Detailed**

```python
FIELD_PATTERNS = {
    # 1. COMPANY NAME EXTRACTION
    "company_name": [
        _field_pattern(
            r"Dénomination[^a-z]*"
            r"|Raison\s+sociale"
            r"|Nom[^a-z]*(?:de\s+la\s+)?(?:société|entreprise)?",
            r"[A-Z][^\n]*?(?=\n|$)",
            stop_labels=["Capital", "Siège", "Adresse", "Durée"]
        ),
    ],
    
    # 2. LEGAL FORM TEXT (fallback extraction, metadata is primary)
    "legal_form_text": [
        _field_pattern(
            r"Forme\s+(?:juridique)?|Type\s+(?:juridique)?\s*(?:de\s+(?:société|entreprise))?",
            r"(?:SARL|Anonyme|SA|SUARL|Autre|Société\s+[A-Za-z]+)",
        ),
    ],
    
    # 3. ADDRESS EXTRACTION
    "address": [
        _field_pattern(
            r"Siège\s+social|Adresse|Sièege[^n]|Localité",
            r"[^\n]*(?:rue|avenue|boulevard|chemin|impasse|place)[^\n]*",
            stop_labels=["Capital", "Durée", "Objet", "Dénomination"]
        ),
    ],
    
    # 4. CAPITAL SOCIAL EXTRACTION
    "capital": [
        _field_pattern(
            r"Capital\s+(?:social)?|au\s+capital\s+de|dotée?\s+d[''']?un\s+capital",
            r"\d[\d\s\.,]*\s*(?:DT|dinars|euros|dinars\s+tunisiens)?",
        ),
    ],
    
    # 5. CORPORATE PURPOSE EXTRACTION
    "corporate_purpose": [
        _field_pattern(
            r"Objet[^a-z]*(?:social)?|Activité|Raison\s+d[''']être",
            r"[A-Za-z][^\n]*(?:logiciel|développement|consultation|service|commerce|industrie)[^\n]*",
            stop_labels=["Durée", "Capital", "Dénomination"]
        ),
    ],
    
    # 6. DURATION EXTRACTION
    "duration": [
        _field_pattern(
            r"Durée|Période|pour\s+une\s+durée\s+de|durée\s+de\s+vie|pour\s+une\s+période",
            r"(?:\d+\s+)?(?:ans?|années?|mois?)",
        ),
    ],
}
```

### **Normalization Functions**

```python
def _normalize_capital(text: str) -> Optional[str]:
    """
    Normalize capital format to: "NNNNNN DT"
    
    Input variations:
    - "50000 DT"
    - "50 000 DT"
    - "50.000 dinars"
    - "50,000 Dinars Tunisiens"
    
    Output: "50000 DT" or None if invalid
    """
    
    # Extract all digits
    digits = re.sub(r"[^\d]", "", text)
    
    if not digits:
        return None
    
    # Limit to reasonable capital range (10 DT to 10M DT)
    value = int(digits)
    if value < 10 or value > 10_000_000:
        return None
    
    # Detect currency
    if re.search(r"eur|euro", text, re.IGNORECASE):
        currency = "EUR"
    elif re.search(r"USD|dollar", text, re.IGNORECASE):
        currency = "USD"
    else:
        currency = "DT"  # Default: Tunisian Dinars
    
    return f"{digits} {currency}"


def _normalize_text_value(text: str) -> str:
    """
    Clean text values:
    - Strip whitespace
    - Fix common OCR errors
    - Remove trailing punctuation
    """
    
    # Strip whitespace
    text = text.strip()
    
    # Fix common OCR substitutions
    text = text.replace("0", "O", 1)  # OCR misreads O as 0 at start
    text = re.sub(r"\s+", " ", text)  # Normalize spaces
    
    # Remove trailing punctuation
    text = re.sub(r"[,.;:]+$", "", text)
    
    return text


def _normalize_person_value(text: str) -> Optional[str]:
    """
    Clean person names before sanitization:
    - Remove appositions (text after comma)
    - Trim whitespace
    
    Example:
        "Ahmed Ben Ali, born 1980" → "Ahmed Ben Ali"
    """
    
    # Split on comma and take first part
    text = text.split(",")[0].strip()
    
    # Split on semicolon
    text = text.split(";")[0].strip()
    
    # Validate not empty
    return text if text else None
```

---

## ROLE_PATTERNS: Extraction de Leadership

### **Role Pattern Definition**

```python
def _line_pattern(
    pattern_str: str,
    description: str = ""
) -> re.Pattern:
    """
    Compile role extraction pattern.
    
    Patterns are case-insensitive and multiline.
    """
    return re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
```

### **All ROLE_PATTERNS**

```python
ROLE_PATTERNS = {
    # Manager (SARL/SUARL primary role)
    "manager": [
        _line_pattern(
            r"(?:est\s+)?gérant[e]?.*?:\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"gérant[e]?[e]?s?\s*:\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})"
        ),
    ],
    
    # Président Directeur Général (combined role - Anonyme/SA)
    "president_directeur_general": [
        _line_pattern(
            r"(?:a\s+nomm[ée]|a\s+d[ée]sign[ée]|nommé[e]?|désign[ée]?)\s*(?:de\s+)?"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})\s*,?\s*"
            r"(?:en\s+qualit[ée]\s+de\s+)?"
            r"(?:président(?:\s*[-\s]\s*|\s+)directeur\s+g[ée]n[ée]ral|"
            r"PDG|p\.d\.g\.)"
        ),
    ],
    
    # Président (council role)
    "president": [
        _line_pattern(
            r"président[e]?\s*(?:du\s+conseil)?\s*[:\s]\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"(?:elected|appointed|nommé[e]?)\s+(?:as\s+)?(?:p|President)\s+"
            r"(?P<value>(?:[A-Z][a-z]+\s+)+[A-Z][a-z]+)"
        ),
    ],
    
    # Directeur Général
    "directeur_general": [
        _line_pattern(
            r"directeur\s+g[ée]n[ée]ral[e]?\s*[:\s]\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"D\.G\.\s*[:\s]\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME)\s+[^,\.\n]{2,140})"
        ),
    ],
    
    # Commissaire aux Comptes (Auditor)
    "auditor": [
        _line_pattern(
            r"commissaire\s+aux\s+comptes\s*[:\s]\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME|CABINET)\s+[^,\.\n]{2,140})"
        ),
        _line_pattern(
            r"auditeur\s*[:\s]\s*"
            r"(?P<value>(?:M\.|MR\.?|MME|MLLE|MONSIEUR|MADAME|CABINET)\s+[^,\.\n]{2,140})"
        ),
    ],
}
```

### **Pattern Matching Function**

```python
def _extract_first(patterns: List[re.Pattern], text: str) -> Optional[str]:
    """
    Try each pattern in sequence, return first match (greedy).
    
    Args:
        patterns: List of compiled regex patterns with 'value' named group
        text: Text to search
    
    Returns:
        First matched value, or None if no match
    """
    
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = match.group("value").strip()
            if value:
                return value
    
    return None
```

---

## Advanced: Capital Normalization Logic

### **Capital Detection & Parsing**

```python
CAPITAL_PATTERNS = [
    r"au\s+capital\s+de\s+(\d[\d\s\.,]*)\s*(?:DT|dinars)",
    r"capital\s+(?:social)?\s*[:\s=]\s*(\d[\d\s\.,]*)",
    r"doté[e]?\s+d[''']?un\s+capital\s+(?:de\s+)?(\d[\d\s\.,]*)",
]

def extract_and_normalize_capital(text: str) -> Optional[str]:
    """
    Multi-pattern capital extraction with fallback.
    
    Handles:
    - Multiple capital mentions (picks first valid one)
    - Various number formats (50000, 50 000, 50.000)
    - Currency detection (DT, dinars, euros)
    
    Strategy: Extract FIRST valid capital only (avoid concatenation)
    """
    
    for pattern_str in CAPITAL_PATTERNS:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        match = pattern.search(text)
        
        if match:
            raw_value = match.group(1)
            return _normalize_capital(raw_value)
    
    return None
```

---

## Challenges & Edge Cases

### **OCR Artifacts**

```
Input: "Dénomination :-   XXXX  SARL"
Problem: Extra spaces, OCR hyphenation
Solution: Normalize spacing in clean_text()

Input: "Au capital de 50000DT50000DT"
Problem: Duplication (OCR error)
Solution: Extract FIRST match only
```

### **Format Variations**

```
Input 1: "Dénomination : MY COMPANY"
Input 2: "Dénomination: MY COMPANY"
Input 3: "Dénomination MY COMPANY"
Solution: Make colon optional in pattern
```

### **Missing or Malformed Labels**

```
Input: "MY COMPANY SARL\n50000 DT\nRue Carthage"
Problem: Company name without "Dénomination:" label
Solution: Sentence fallback regex (extracts pattern-like values)
```

---

## Performance: Pattern Compilation

```python
# Load at module initialization (once)
COMPILED_FIELD_PATTERNS = {
    field: [
        p if isinstance(p, re.Pattern) else re.compile(p)
        for p in patterns
    ]
    for field, patterns in FIELD_PATTERNS.items()
}

COMPILED_ROLE_PATTERNS = {
    role: [
        p if isinstance(p, re.Pattern) else re.compile(p)
        for p in patterns
    ]
    for role, patterns in ROLE_PATTERNS.items()
}

# Usage: Reference compiled versions
def extract_field(field_name: str, text: str) -> Optional[str]:
    patterns = COMPILED_FIELD_PATTERNS[field_name]
    return _extract_first(patterns, text)
```

**Performance:** ~1ms per notice (5000 patterns compiled once at startup)

