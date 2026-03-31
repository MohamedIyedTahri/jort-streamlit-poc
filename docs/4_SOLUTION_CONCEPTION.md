# 4. Solution Proposée & Conception

## Architecture Générale: Pipeline d'Extraction 6-Étapes

Infyntra propose une architecture systématique:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. AUTOMATED COLLECTION                                        │
│  Scraping archives JORT (2013-2025) depuis Imprimerie Officielle│
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. DOCUMENTARY ENGINEERING                                     │
│  Handling page geometry: headers/footers, column isolation       │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. OPTICAL EXTRACTION (OCR)                                    │
│  Tesseract + OpenCV: pixels → characters à l'échelle industrielle│
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. SEMANTIC SURGERY                                            │
│  Isolation annonces individuelles via Regex (admin reference)   │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. LINGUISTIC INTELLIGENCE                                     │
│  Extraction entités + Handling jargon juridique                 │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. JSON STRUCTURING                                            │
│  Normalization → JSON files                                      │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
                  DATABASE INTEGRATION
                  ECONOMIC INTELLIGENCE
```

---

## Ma Solution: Pipeline Spécialisé pour Constitutions

Je propose un **sous-pipeline focalisé** qui implémente les étapes 3-6 pour les **annonces de constitution**:

### **Étapes du Pipeline**

```
constitution/
  ├─ anonyme/2004/001Journal.../notice.txt  ← INPUT
  ├─ anonyme/2004/002Journal.../notice.txt
  └─ ...

                    ↓ [STAGE 1: ENCODING DETECTION]
           Read with fallback (UTF-8 → CP1252 → Latin-1)

                    ↓ [STAGE 2: TEXT CLEANING]
              Raw OCR → Normalized Text
         (hyphenation, spacing, noise removal)

                    ↓ [STAGE 3: CONSTITUTION FILTER]
          is_constitution_notice() → boolean
     (keywords + structure detection)

                    ↓ [STAGE 4: FIELD EXTRACTION - REGEX PHASE]
              Regex patterns on FIELD_PATTERNS dict
         (company_name, address, capital, duration, etc.)

                    ↓ [STAGE 5: LEADERSHIP EXTRACTION - REGEX]
              Role patterns on ROLE_PATTERNS dict
         (Gérant, Président, Directeur Général, Auditeur)

                    ↓ [STAGE 6: NLP FALLBACK (optional)]
              spaCy fr_core_news_sm enrichment
         (for missing fields, or leadership in complex cases)

                    ↓ [STAGE 7: FRIEND ENRICHMENT (optional)]
              Reference data validation & filling
         (compare with Friend dataset, fill gaps)

                    ↓ [STAGE 8: NOT_APPLICABLE RESOLUTION]
              Mark fields as N/A per legal form
         (e.g., Anonyme without Président → mark Président as N/A)

                    ↓ [STAGE 9: OUTPUT]
                extracted_notices.json
         [Array of structured records with statistics]
```

---

## Composants Clés de Mon Implémentation

### **1. Text Cleaner (`extractor/cleaner.py`)**

**Objectif:** Transformer OCR brut en texte exploitable.

**Fonctions:**
- Hyphenation removal: `word-\nsubword` → `wordsubword`
- Spacing normalization: multi-espaces → simple space
- Bruit punctuation: excessive caractères → removed
- Blank lines: 3+ lignes vides → 2 lignes

```python
def clean_text(raw_text: str) -> str:
    """Normalize OCR text for extraction."""
    # 1. Fix hyphen-split words across linebreaks
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    
    # 2. Normalize spacing around colons
    text = re.sub(r" :", ":", text)
    
    # 3. Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    
    # 4. Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()
```

### **2. Pattern Library (`extractor/patterns.py`)**

**Objectif:** Définir tous les regex patterns pour extraction.

Structure:
```python
FIELD_PATTERNS = {
    "company_name": [
        _field_pattern(r"Dénomination|Raison sociale", ...),
        _field_pattern(r"Nom de la [...] sociale", ...),
        ...
    ],
    "legal_form_text": [
        _field_pattern(r"Forme|Type", ...),
        ...
    ],
    "address": [
        _field_pattern(r"Siège social|Adresse|Sièege [^n]", ...),
        ...
    ],
    "capital": [
        _field_pattern(r"Capital social|au capital de", ...),
        ...
    ],
    # ... 8 more fields
}

ROLE_PATTERNS = {
    "president_directeur_general": [...],
    "president": [...],
    "directeur_general": [...],
    "auditor": [...],
}
```

**12 patterns primaires pour:**
- company_name, legal_form_text, address, capital
- corporate_purpose, duration
- manager (SARL/SUARL)
- president, directeur_general, president_directeur_general, auditor

### **3. Constitution Notice Detector (`extractor/parser.py`)**

**Fonction:** `is_constitution_notice(text: str) -> bool`

Trois critères:
1. **Positive markers:** "constitution", "création", "notice au public"
2. **Negative markers:** "convocation", "ordre du jour"
3. **Structural score:** Compte les types labels (≥3 = constitution)

Logique:
```python
def is_constitution_notice(text: str) -> bool:
    has_positive = any(m in text for m in POSITIVE_MARKERS)
    has_negative = any(m in text for m in NEGATIVE_MARKERS)
    
    # If has negative markers without positive, likely not constitution
    if has_negative and not has_positive:
        return False
    
    # If has positive markers, likely constitution
    if has_positive:
        return True
    
    # Otherwise, count structural indicators
    structural_score = _count_structural_labels(text)
    return structural_score >= 3
```

### **4. Notice Parser (`extractor/parser.py`)**

**Fonction:** `parse_notice(cleaned_text: str, metadata: Dict) -> Dict[str, object]`

**Étapes:**

1. **Regex extraction** pour tous les FIELD_PATTERNS
   - Applique normalizers spécifiques au champ
   - `_normalize_capital()` pour monnaie
   - `_normalize_person_value()` pour noms
   - `_normalize_text_value()` pour texte général

2. **Leadership extraction** (form-specific)
   - SARL/SUARL: manager seulement (via patterns + sentence fallback)
   - Anonyme: council complet (roles multiples)

3. **NLP fallback** (si champs manquent)
   - `extract_core_fields_with_nlp()` pour capital/address/company
   - `extract_leadership_with_nlp()` pour gouvernance complexe

4. **Not-applicable resolution**
   - Anonyme WITHOUT leadership signals → manager = N/A
   - Autre = souvent N/A pour plusieurs champs

### **5. NLP Enrichment (`extractor/nlp_enrichment.py`)**

**Fonction:** spaCy fallback pour les cas regex manque

**Capacités:**
- Indentation-aware governance section detection ("Conseil d'administration")
- Person NER recognition (PERSON labels spaCy)
- Lemma-based nomination detection ("nommer", "designer", "élire")
- Name extraction before role markers

```python
def extract_leadership_with_nlp(text: str) -> Dict[str, Optional[str]]:
    """Extract governance using spaCy NLP."""
    nlp = load_spacy_model()
    doc = nlp(text)
    
    result = {}
    
    # Find governance sections
    for section_text in _indentation_sections(doc):
        for sent in section_text.sents:
            # Check for nomination triggers
            if _has_nomination_lemma(sent):
                # Extract person via NER + regex
                person = _extract_person_ner(sent)
                role = _extract_role_marker(sent)
                
                if person:
                    result[role] = person
    
    return result
```

### **6. Friend Enrichment (`extractor/enrichment.py`)**

**Fonction:** Validation et remplissage via reference data

```python
def load_friend_index(friend_data_dir: Path) -> Dict[str, Dict[str, str]]:
    """Load Friend reference dataset index."""
    index = {}
    for json_file in friend_data_dir.glob("*.json"):
        ref = json_file.stem  # filename without extension
        friend_data = json.loads(json_file.read_text())
        
        # Extract all key-value candidates
        candidates = {}
        for key, value in _iter_pairs(friend_data):
            field = _field_from_key(key)
            if _valid_for_field(field, value):
                candidates[field] = value
        
        index[ref] = candidates
    
    return index

def apply_friend_fallback(
    record: Dict, 
    notice_text: str,
    reference: str,
    friend_index: Dict
) -> int:
    """Fill empty record fields from Friend data."""
    if reference not in friend_index:
        return 0
    
    added = 0
    for field, candidate in friend_index[reference].items():
        if record[field] is None:  # Only fill empty fields
            # Validate candidate is present in source text
            if _candidate_in_text(candidate, notice_text):
                record[field] = candidate
                added += 1
    
    return added
```

---

## Comparaison: Regex vs. NLP vs. Friend

| Technique | Avantages | Limitations | Coverage |
|-----------|-----------|-------------|----------|
| **Regex** | Rapide, précis, no ML | Inflexible, beat cases variés | ~70% |
| **NLP (spaCy)** | Flexible, contextuel | Plus lent, less precise on noisy text | ~20% |
| **Friend** | Ground truth, High precision | Seulement 2004, limited coverage | ~5% |

**Hybrid approach:** Cascade avec fallback améliore précision AND recall.

---

## Métriques de Succès

Pour chaque annonce extraite:
- ✅ 100% des champs applicables ou marqués N/A
- ✅ Pas de champs vides sans raison
- ✅ Capital toujours en format `NNNN DT` ou N/A
- ✅ Noms personnels sanitisés (appositions removed)
- ✅ Enrichment Friend appliqué où applicable
- ✅ Stats explicites (scanned, parsed, skipped, errors, enriched)

---

## Output Structure

```json
[
  {
    "company_name": "TECH SOLUTIONS SARL",
    "legal_form": "SARL",
    "year": 2004,
    "issue_number": 1,
    "source_file": "123-constitution.txt",
    "address": "123 Rue Carthage, Tunis",
    "capital": "50000 DT",
    "corporate_purpose": "Développement logiciels",
    "duration": "99 ans",
    "manager": "Ahmed Ben Ali",
    "president": null,
    "directeur_general": null,
    "auditor": null,
    "not_applicable_fields": ["president", "directeur_general", "auditor"]
  },
  ...
]
```

**Caractéristiques:**
- Tous les 12 champs présents (null ou value ou "N/A")
- Metadata complète (year, issue_number, source_file)
- Tracçabilité (`not_applicable_fields`) pour analyses

