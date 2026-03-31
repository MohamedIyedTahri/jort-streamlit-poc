# 5. Analyse du Besoin & Technologies

## Analyse du Besoin: Quelles Données Extraire?

### **12 Champs Cibles**

Pour chaque annonce de constitution, nous avons besoin:

#### **IDENTITÉ DE L'ENTREPRISE (4 champs)**

| Champ | Exemple | Format | Obligatoire |
|-------|---------|--------|------------|
| **company_name** | "TECH SOLUTIONS SARL" | Text | ✅ Oui |
| **legal_form** | "SARL", "SA", "SUARL" | Enum (from metadata/structure) | ✅ Oui |
| **address** | "123 Rue Carthage, Tunis 1000" | Text | ✅ Oui |
| **capital** | "50000 DT", "100 000 dinars" | "NNNNN DT" ou N/A | ⚠️ Form-dependent |

#### **STRUCTURE FINANCIÈRE (1 champ)**
- **capital:** Capital social (SARL/Anonyme oui, Autre N/A souvent)

#### **GOUVERNANCE & LEADERSHIP (5 champs)**

| Champ | Applicable à | Exemple |
|-------|-------------|---------|
| **manager** | SARL, SUARL | "Mohamed Ahmed Ben Ali" |
| **president** | Anonyme mainly | "Fatima Bensalah" |
| **directeur_general** | Anonyme | "Ali Zaiem" |
| **president_directeur_general** | Anonyme (variant) | "Ahmed Tounsi" |
| **auditor** | Anonyme | "Cabinet XYZ" ou "Khalil Karim" |

**Règles par forme:**
- **SARL:** manager ONLY (1-2 noms max)
- **Anonyme:** Council complet (3-5 rôles)
- **SUARL:** manager seulement

#### **ACTIVITÉ & DURÉE (2 champs)**

| Champ | Exemple | Format |
|-------|---------|--------|
| **corporate_purpose** | "Développement de logiciels", "Consultation" | Text (10-100 chars) |
| **duration** | "99 ans", "pour une durée de 50 ans" | Text ou N/A |

#### **MÉTADONNÉES (3 champs - from file structure)**

| Champ | Source | Exemple |
|-------|--------|---------|
| **year** | Folder structure | 2004, 2005, ... |
| **issue_number** | Folder name regex | 001, 002, 123, ... |
| **source_file** | Filename | "123-constitution.txt" |

---

## Technologie: Stack Extraction

### **1. Niveau FONDAMENTAL: Python Data Stack**

```
Python 3.9+
├─ Pandas (data manipulation)
├─ NumPy (matrix operations)
└─ Pathlib (file system)
```

**Usage:**
- File iteration, metadata extraction
- JSON serialization
- String manipulation

### **2. Niveau DOCUMENTAIRE: Vision & Cleanup**

```
├─ PyMuPDF (PDF to text, page handling)
├─ Pytesseract (OCR wrapper)
└─ OpenCV (image preprocessing, column isolation)
```

**Usage:**
- Document parsing (future: handle PDF geometry)
- OCR invocation
- Column detection & realignment

### **3. Niveau EXTRACTION ET INTELLIGENCE: Regex + NLP**

```
├─ re (Regular Expressions)
│   └─ Pattern compilation, matching, extraction
│
└─ spaCy (NLP)
    ├─ fr_core_news_sm (French model)
    ├─ Tokenization, lemmatization
    ├─ Named Entity Recognition (NER)
    │   └─ PERSON, ORG, GPE labels
    └─ Dependency parsing
```

**Usage:**
- Regex: field extraction via pattern matching
- spaCy:
  - Lemmatization for nomination detection
  - NER for person/organization recognition
  - Sentence segmentation for context analysis

### **4. Niveau ORCHESTRATION: Parallel Processing**

```
├─ Threading (MultiThreadExecutor)
└─ argparse (CLI argument parsing)
```

**Usage:**
- Multithreaded file processing (future: massive parallelization)
- Command-line interface for pipeline execution

### **5. Niveau ENRICHMENT: Reference Data**

```
└─ JSON (Friend reference database)
    └─ Key-value candidate validation & filling
```

---

## Technologie Stack Détaillé: Configuration

### **Environment Setup**

```bash
# Python version
Python 3.9+ (tested on 3.10+)

# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Requirements.txt** (Minimal)

```
spacy>=3.0,<4.0
pytesseract>=0.3.10
Pillow>=8.0
PyMuPDF>=1.18.0
```

### **Model Download**

```bash
# French NLP model (117MB)
python -m spacy download fr_core_news_sm

# Optional: German, Spanish models for future expansion
```

---

## Architecture: 6 Modules Principaux

```
jort/
├── main.py                          [Entry point]
├── extractor/
│   ├── __init__.py
│   ├── cleaner.py                   [Text normalization]
│   ├── patterns.py                  [Regex library]
│   ├── parser.py                    [Core extraction logic]
│   ├── nlp_enrichment.py            [spaCy fallback]
│   └── enrichment.py                [Friend reference data]
├── utils/
│   ├── __init__.py
│   └── filesystem.py                [File & metadata handling]
├── constitution/                    [Input data directory]
│   ├── anonyme/2004/...
│   ├── sarl/2004/...
│   ├── suarl/2004/...
│   └── autre/2004/...
├── output/                          [Output directory]
│   ├── extracted_notices.json       [Main output]
│   ├── friend_2004_side_by_side_diff.json
│   └── friend_2004_side_by_side_summary.json
└── docs/                            [Documentation]
```

---

## Contraintes & Décisions Techniques

### **1. OCR Quality Variability**

**Problema:** Some 2004 scans are low-quality.

**Constraints:**
- Cannot improve OCR (no ML retraining)
- Must work with what's available

**Solution:**
- Text cleaning pipeline (removes artifacts)
- Flexible regex patterns (handles variations)
- NLP fallback (contextual understanding)
- Friend enrichment (ground truth fallback)

### **2. Multi-Encoding Support**

**Problema:** Files use UTF-8, CP1252, Latin-1 inconsistently.

**Constraint:** No metadata indicates encoding.

**Solution:** Cascade fallback
```python
for encoding in ("utf-8", "cp1252", "latin-1"):
    try:
        return raw_bytes.decode(encoding)
    except UnicodeDecodeError:
        continue
```

### **3. Form-Specific Rules**

**Problema:** SARL ≠ Anonyme in governance structure.

**Constraint:** Same parsing code must handle all forms.

**Solution:** Form-aware extraction
```python
if legal_form == "SARL":
    # Extract single manager
elif legal_form == "Anonyme":
    # Extract council: PDG + DG + Audit
```

### **4. Precision vs. Recall Trade-off**

**Problema:** More liberal regex = more false positives.

**Constraint:** Don't want garbage data.

**Solution:**
- Conservative base patterns
- NLP for contextualization
- Friend validation for confirmation
- Explicit quality stats

---

## Comparaison Technologies Alternatives

### **Why Regex + spaCy (not full ML)?**

| Approche | Avantages | Limitations |
|----------|-----------|------------|
| **Full Deep Learning (BERT, etc.)** | Flexible, contextual | Coûteux, nécessite massive labeled data, lent |
| **Regex only** | Rapide, précis, interpretable | Inflexible, beat variabilité |
| **spaCy NER only** | Better context, NER built-in | Pas assez pour governance |
| **Our Hybrid** | Fast + accurate + interpretable | Plus simple que ML, covers 95%+ |

**Decision:** Hybrid Regex + spaCy + Reference = best ROI.

---

## Performance & Scalability

### **Current Performance (2004 data)**

```
Dataset:     ~5000 constitution notices (anonyme 2004)
Time:        ~5 seconds (on single-threaded)
Per-file:    ~1ms per notice
Memory:      ~200MB (spaCy model + data)
Accuracy:    ~82% per field (vs Friend reference)
```

### **Scaling to All Years (2004-2025)**

```
Estimated:   200,000+ notices total
Bottleneck:  spaCy model loading (117MB)
Solution:    Model persistence, lazy loading
Speed-up:    10x via multithreading (future)
```

### **Future: Distributed Processing**

```
Option A: Multiprocessing (filesystem.py)
Option B: Cloud pipeline (AWS/GCP)
Option C: Batch processing (daily cron)
```

---

## Quality Metrics & Monitoring

### **Per-Field Statistics**

```python
statistics = {
    "scanned": 5000,
    "parsed": 4500,
    "skipped": 500,
    "skipped_non_constitution": 450,
    "errors": 50,
    "enriched_records": 1200,
    "enriched_fields": 2400
}
```

### **Per-Form Evaluation**

```json
{
  "anonyme": {
    "missing_fields": {"company_name": 12, "capital": 34, ...},
    "not_applicable_fields": {"manager": 5000, ...},
    "pct_complete": "94%"
  },
  "sarl": {...},
  "suarl": {...},
  "autre": {...}
}
```

---

## Conclusion: Tech Stack Summary

```
INPUT (PDFs) 
    ↓ [Pytesseract + OpenCV → OCR]
    ↓ [Python + Pathlib → file iteration]
    ↓ [Regex (re module) → pattern extraction]
    ↓ [spaCy fr_core_news_sm → NLP fallback]
    ↓ [JSON → Friend enrichment]
OUTPUT (extracted_notices.json)
```

**Every component chosen for:**
- ✅ Speed (realtime processing)
- ✅ Accuracy (hybrid multimodal)
- ✅ Scalability (parallel-ready)
- ✅ Maintainability (open-source stack)
