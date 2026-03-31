# 1. Présentation de l'Entreprise & du Projet

## Infyntra: De l'opacité documentaire à l'intelligence économique

### **Mission Globale**
Infyntra est une plateforme d'automatisation conçue pour **transformer les documents juridiques non-structurés en intelligence économique exploitable**.

L'objectif principal : **extraire automatiquement les informations clés des communications juridiques officielles et les structurer pour des analyses macro-économiques et micro-business**.

### **Contexte: Le Journal Officiel Tunisien (JORT)**

Le **JORT (Journal Officiel de la République Tunisienne)** publie quotidiennement **des milliers d'annonces légales** concernant:
- **Constitutions d'entreprises** (nouvelles sociétés)
- **Modifications légales** (changements d'adresse, capital, management)
- **Liquidations** (cessation d'activités)
- **Décisions judiciaires** (faillites, procédures)

**Le problème:** Ces annonces sont distribuées en **PDF non-indexés**, avec:
- Texte brut sans structure
- Qualité OCR variable (scans numérisés)
- Mises en page multi-colonnes
- Encodages mixtes (UTF-8, Latin-1, CP1252)

### **Ma Contribution au Projet**

J'ai développé un **pipeline d'extraction spécialisé pour les annonces de constitution** du JORT, en me concentrant sur:

1. **Nettoyage de texte robuste** — Gestion des artefacts OCR et des encodages multiples
2. **Extraction structurée par regex** — Pattern library pour les champs légaux tunisiens
3. **Enrichissement NLP** — Fallback spaCy pour les cas que la regex ne peut pas traiter
4. **Validation par données de référence** — Utilisation du dataset "Friend" pour valider les extractions manquantes

### **Résumé de la Solution Infyntra**

```
Annonces PDF JORT (brutes, non-indexées)
         ↓
    [Collection Automatisée]
         ↓
    [Ingénierie Documentaire] (géométrie PDF, nettoyage)
         ↓
    [Extraction Optique (OCR)]  Tesseract + OpenCV
         ↓
    [Analyse Sémantique] (isolation des annonces individuelles)
         ↓
    [Intelligence Linguistique] (extraction entités, roles)
         ↓
    [Structuration JSON] (normalisation en données exploitables)
         ↓
JSON Structuré → Base de données → Intelligence économique
```

### **Données Cibles Extraites**

Pour chaque annonce de constitution, on extrait:

| Catégorie | Champs |
|-----------|--------|
| **Identité Entreprise** | Dénomination sociale, Forme juridique, Adresse |
| **Structure Financière** | Capital social, Devise |
| **Governance** | Gérant, Président, Directeur Général, Auditeur, Conseil |
| **Traces Légales** | Tribunal d'enregistrement, Numéro registre commercial, Date publication |

### **Applications Envisagées**

1. **Recherche Macro-économique:** Cartographier la croissance économique régionale sur 10+ ans
2. **Intelligence Concurrence (B2B):** Alertes sur new entrants, changements de management
3. **LegalTech:** Structuration de données pour le domaine juridique
4. **Lifecycle Mapping:** Timelines d'entreprises (création → modifications → liquidation)
5. **Knowledge Graphs:** Connexions entre entreprises (adresses partagées, managers communs)

### **État Actuel**

- ✅ **Pipeline 2004** : Constitution notices extraction pour l'année 2004 (base de données Friend disponible)
- ✅ **Validation interne** : Comparaison pipeline vs Friend pour identifier les gaps
- 🔄 **Scaling** : Extension à 2005, 2006, etc.
- 🔄 **Coverage** : Autres types d'annonces (modifications, liquidations)

---

## Focus: Pipeline d'Extraction des Annonces de Constitution

Le reste de cette documentation détaille **mon implémentation spécialisée** pour les annonces de constitution (notices de création d'entreprise), qui constitue la phase 1 d'Infyntra.

**Cible:** Transformer les annonces JORT en JSON structuré avec:
- 100% des champs applicables extraits ou marqués "N/A"
- Fallback NLP pour les cas complexes (governance dispersée)
- Enrichissement Friend pour les extractions manquées
- Statistiques de qualité explicites
