# 3. Étude de l'Existant

## État des Lieux Avant Implémentation

### **Ce qui existait déjà**

Infyntra avait défini:
- ✅ Architecture générale (6 étapes: Collection → OCR → Semantic Surgery → JSON)
- ✅ Vision des données extraites
- ✅ Dataset Friend (données de référence pour 2004)
- ✅ Besoins business (mapping économique, competitor intelligence)

### **Ce qui manquait**

- ❌ Code spécialisé pour annonces de **constitution** (vs. autres types)
- ❌ Patterns regex optimisés pour le **vocabulaire juridique tunisien**
- ❌ Handling des formes juridiques **multiples** (SARL, Anonyme, etc.)
- ❌ Extraction de **governance/leadership** (noms de managers, directeurs)
- ❌ Integration du **NLP** (pas de fallback intelligent)
- ❌ Validation contre **data de référence** (Friend enrichment)
- ❌ Analyse du **delta** (pipeline vs Friend)
- ❌ Statistiques de **qualité** (par type, par champ)

---

## Découvertes Clés au Cours du Projet

### **1. Problèmes d'Encodage Réels**

**Découverte:** Les PDFs JORT ne sont PAS simplement UTF-8.

```python
# Solution implémentée:
def _read_notice_text(file_path: Path) -> str:
    raw_bytes = file_path.read_bytes()
    
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # Last-resort: decode with error replacement
    return raw_bytes.decode("utf-8", errors="replace")
```

**Réalité:** Certains fichiers utilisent CP1252 (Windows Latin), d'autres Latin-1 (ISO-8859-1).

### **2. Distinctions de Formes Juridiques Critiques**

**Découverte:** Chaque forme a des **règles d'extraction différentes**.

| Forme | Manager Field | Notes | Nombre Leaders |
|-------|---------------|-------|-----------------|
| **SARL** | `gérant` (simple) | Un seul gérant | 1 |
| **SUARL** | `gérant` (simple) | Gérant unique | 1 |
| **Anonyme** | Conseil complet | PDG, Directeur Général, Président, Auditeur | 3-5 |
| **Autre** | Variable | N/A si association | 0-N |

**Challenge:** Une annonce Anonyme peut avoir **5+ noms dans la section governance**.

### **3. Capital Social: Variabilité Extrême**

**Découverte:** Le capital apparaît en **10+ formats** différents:

```
1. "Au capital de 50000 DT"
2. "Capital social: 50 000 DT"
3. "Capital: 50.000 dinars"
4. "Capital social de 50.000 Dinars Tunisiens"
5. "Doté d'un capital initial de 50000"
6. "Montant du capital: 50.000,00 DT"
7. Souvent répété 2-3 fois différemment
```

**Solution adoptée:** Capture du **premier montant** uniquement (évite les doublons).

### **4. Gouvernance Dispersée et Contextuelle**

**Découverte:** Leadership n'est JAMAIS structuré uniformément.

**Cas 1: Structure claire (rare)**
```
Gérant : M. Ahmed Ben Ali
```

**Cas 2: Multi-ligne (courant)**
```
Premier conseil d'administration :
M. Mohamed Tounsi, Président
M. Ali Zaiem, Directeur Général
Mme Fatima Aouadi, Auditeur
```

**Cas 3: Narrative (très courant)**
```
Il a été décidé lors de l'assemblée générale
de nommer M. Ahmed en qualité de Président
Directeur Général
```

**Solution:** Deux-niveaux fallback:
1. Regex patterns (couvre 60-70%)
2. NLP avec reconnaissance d'entités spaCy (couvre 20-30%)
3. Reference enrichment (couvre les 5-10%)

### **5. Détection Constitution vs. Autres Types**

**Découverte:** Pas toutes les annonces sont des **constitutions**.

Beaucoup sont:
- **Convocations** (appels à assembler)
- **Procès-verbaux AG** (résultats de réunions)
- **Modifications** (changements adresse/capital)
- **Liquidations** (fin d'activité)

**Impact:** Un filtrage inapproprié = pollution du dataset.

**Solution:** Multi-critère
```python
def is_constitution_notice(text: str) -> bool:
    # Positive markers (constitution keywords)
    positive_markers = [
        "constitution", "création", 
        "notice au public", 
        "assemblée générale constitutive"
    ]
    
    # Negative markers (non-constitution keywords)
    negative_markers = [
        "convocation", "ordre du jour",
        "assemblée ordinaire", "assemblée extraordinaire"
    ]
    
    # Structural score (count label types)
    has_positive = any(m in text for m in positive_markers)
    has_negative = any(m in text for m in negative_markers)
    structural = count_label_types(text)  # ≥3 labels = likely constitution
    
    return (has_positive and not has_negative) or (structural >= 3)
```

### **6. Cleanup OCR: Nécessité Critique**

**Découverte:** OCR raw == inutilisable pour regex.

**Problèmes OCR observés:**
```
Input:
"Dénomination:-
	
  Xxxxxx	SARL
Adre-
sse xxx: Tunis"

Output (brut):
company_name = "XXXXX SARL Adre sse" ❌
```

**Solution:** Pipeline de nettoyage:
```python
def clean_text(raw_text: str) -> str:
    # 1. Linbreaks + hyphenation
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    
    # 2. Normalize spacing
    text = re.sub(r" :", ":", text)
    text = re.sub(r" {2,}", " ", text)
    
    # 3. Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()
```

### **7. Pipeline Require Fallback Généré (pas deterministe)**

**Découverte:** Aucun pattern regex seul est suffisant.

**Statistiques observées (2004 data):**
- Regex only: ~72% precision, ~60% recall
- + NLP fallback: ~82% precision, ~75% recall  
- + Friend enrichment: ~88% precision, ~80% recall

**Conclusion:** Cascade technique est NÉCESSAIRE.

---

## Reference Data: Friend Dataset

### **Présentation du Dataset Friend**

- **Source:** Données Infyntra existantes pour 2004 (anonyme focus)
- **Format:** JSON files par reference (num - constitution.json)
- **Contenu:** Key-value pairs with various candidate values
- **Usage:** Validation & enrichment des extractions manquées

### **Exemple Analyse Friend**

```json
{
  "123-constitution": {
    "Dénomination": "TECH SOLUTIONS SARL",
    "Siège": ["123 Rue Carthage", "Commerce, Tunis"],
    "Capital": ["50000", "50000 DT"],
    "Gérant": ["M. Ahmed Ben Ali"],
    "Président": ["Absent"],
    ...
  }
}
```

**Utilisation:**
1. Parser extrait `company_name="" (failed)`
2. Friend a `"Dénomination": "TECH SOLUTIONS SARL"`
3. Si pas de doublons ou bruit → fallback à Friend value
4. Logs le enrichment pour tracking

---

## État d'Avancement Pré-Pipeline

| Composant | Status |
|-----------|--------|
| Documentation Infyntra | ✅ Existant |
| Dataset JORT (2004) | ✅ Disponible |
| Friend reference data | ✅ Disponible |
| Code extraction | ❌ À développer |
| Validation | ❌ À développer |
| Analysis tools | ❌ À développer |

**Conclusion:** Mon rôle = **transformer specifications en code exécutable** avec tests et validation.
