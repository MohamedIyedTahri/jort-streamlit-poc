# 2. Contexte du Projet & Problématique

## Le Paradoxe de l'Information Juridique

### **Réalité Actuelle**

Le JORT publie **des milliers de communications gouvernementales quotidiennes**, incluyant:
- **Annonces de constitution d'entreprises** (principalement)
- Changements statutaires
- Faillites et liquidations
- Décisions administratives

Ces annonces contiennent précisément les **données macro-économiques** que recherchent:
- Les analystes économiques (croissance secteur/région)
- Les concurrents (intelligence de marché)
- Les investisseurs (opportunity sourcing)
- Les régulateurs (surveillance économique)

### **Le Problème Technique**

Les annonces JORT sont **inaccessibles pour traitement automatisé** à cause de:

| Barrière | Impact |
|----------|--------|
| **Pas d'indexation** | Recherche manuelle impossible sur 10+ ans de données |
| **Format PDF non-structuré** | Pas de métadonnées, juste un flux textuel |
| **Mise en page multi-colonnes** | Colonnes entrelacées → texte fragmenté à la lecture |
| **Orientation droite-à-gauche (RTL)** | Arabe + Français en même document |
| **Blocs texte superposés** | OCR recompose mal l'ordre de lecture |
| **Qualité d'OCR variable** | Scans anciens = caractères mal reconnus |
| **Encodages mixtes** | UTF-8, Latin-1, CP1252 sans indication |

### **Exemple Concret: OCR Brut vs. Attendu**

```
RAW OCR OUTPUT:
"Dénomination:  xxxxxx SARL
Siège: 123 rue xxx
Au capital de 50000 DT" 
Gérant: M. Ahmed Ben Ali..."

VS.

STRUCTURED DATA NEEDED:
{
  "company_name": "xxxxxx SARL",
  "address": "123 rue xxx",
  "capital": "50000 DT",
  "legal_form": "SARL",
  "manager": "Ahmed Ben Ali"
}
```

### **Obstacles Spécifiques à la Tunisie**

1. **Vocabulaire juridique français spécialisé**
   - "Gérant" (SARL)
   - "Président Directeur Général" (Anonyme)
   - "Commissaire aux comptes"
   - Abréviations inconsistentes (Mme/Madame/Mlle)

2. **Formes juridiques multiples**
   - SARL (Société à Responsabilité Limitée)
   - Anonyme (Société Anonyme/SA)
   - SUARL (Société Unipersonnelle à Responsabilité Limitée)
   - Autre (associations, etc.)
   - Chacune a des règles différentes (qui signe? combien de directors?)

3. **Données personnelles variables**
   - Single founder (SUARL) → un gérant uniquement
   - Multiple directors (Anonyme) → conseil d'administration entier
   - Appellations mixtes (M., Monsieur, Mr, Mme, Madame)

4. **Capital social en formats variables**
   - "50000 DT" vs "50 000 DT" vs "50.000 DT"
   - "50000 Dinars Tunisiens"

### **Défi Central: Extraction Semi-Structurée**

L'information existe dans les PDFs mais sous forme **semi-structurée**:

```
Exemple simplifié d'annonce JORT:

Avis de constitution

Dénomination: TECH SOLUTIONS SARL
Siège social: 123 Rue de Carthage, Tunis 1000
Durée: 50 ans ou 99 ans
Capital social: 100000 DT (100 mille dinars)
Objet social: Développement de logiciels

Gérant:
M. Mohamed Ahmed  
Adresse personnelle: Tunis

Premier conseil d'administration:
Président: Mme Fatima Bensalah
Directeur Général: M. Ali Zaiem
Commissaire aux comptes: Cabinet XYZ

Au capital de 150000 Dinars Tunisiens
```

**Défis:**
1. Labels (Dénomination, Siège, Gérant) peuvent estar sur même ligne que valeur
2. Valeurs peuvent s'étendre sur plusieurs lignes
3. Format de noms personnels varie énormément
4. Capital peut être indiqué plusieurs fois différemment
5. Gouvernance peut être structurée ou narrative

### **Objectif du Pipeline**

Créer un système capable de:
✅ Lire PDFs bruts quelconque  
✅ Normaliser texte (OCR noise, encoding)  
✅ Identifier les annonces constitution vs autres types  
✅ Segmenter l'annonce en sections (entête, identité, governance, footer)  
✅ Extraire 12 champs clés avec haute précision  
✅ Gérer les cas limites via fallback NLP  
✅ Valider extractions par comparaison with reference data  
✅ Produire JSON exploitable pour downstream analysis  

### **Approche Hybride Nécessaire**

Aucune technique seule ne suffit:

- **Regex seule** → Échoue sur variations de format
- **NLP/ML seule** → Trop coûteux, précision insuffisante sur données anciennes
- **Template matching** → Pas assez flexible

**Solution:** **Cascade de techniques**
1. Regex patterns optimisés (rapide, 70-80% coverage)
2. NLP fallback (spaCy) pour compléter (+ 15-20%)
3. Reference data enrichment (Friend) pour valider/combler les gaps (+ 5%)

---

## Summary: Pourquoi c'est Difficile?

| Élément | Raison |
|---------|--------|
| **Pas de structure** | PDF = pixels convertis en texte, pas de marquage |
| **Variabilité lexicale** | Même concept = 10 formulations différentes |
| **OCR imparfait** | Vieux scans = caractères mal reconnus |
| **Formes variables** | SARL vs Anonyme = règles extractions différentes |
| **Données multi-cultures** | Arabe + Français + noms personnels complexes |

**Notre solution: Robustness par redondance** (regex + NLP + reference validation)
