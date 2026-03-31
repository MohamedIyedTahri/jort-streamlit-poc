from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractor.cleaner import clean_text
from extractor.enrichment import apply_friend_fallback, load_friend_index
from extractor.parser import is_constitution_notice, parse_notice


YEAR_MIN = 2004
YEAR_MAX = 2014


st.set_page_config(
    page_title="JORT Proof of Concept",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_json_records(json_path: str) -> List[Dict[str, Any]]:
    path = Path(json_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


@st.cache_data(show_spinner=False)
def load_markdown_file(md_path: str) -> str:
    path = Path(md_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def load_friend_index_cached(friend_dir: str) -> Dict[str, Dict[str, str]]:
    path = Path(friend_dir)
    if not path.exists() or not path.is_dir():
        return {}
    return load_friend_index(path)


def records_to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def compute_missing_stats(df: pd.DataFrame, fields: List[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["field", "missing_count", "missing_rate"])

    rows = []
    total = len(df)
    for field in fields:
        if field not in df.columns:
            missing_count = total
        else:
            missing_count = int(df[field].isna().sum())
        rows.append(
            {
                "field": field,
                "missing_count": missing_count,
                "missing_rate": round((missing_count / total) * 100, 2),
            }
        )
    return pd.DataFrame(rows)


def compute_record_completeness(record: Dict[str, Any], fields: List[str]) -> float:
    present = 0
    for field in fields:
        value = record.get(field)
        if value is not None and str(value).strip() != "":
            present += 1
    if not fields:
        return 0.0
    return round((present / len(fields)) * 100, 2)


def filter_df_by_year_range(df: pd.DataFrame, year_range: tuple[int, int]) -> pd.DataFrame:
    if df.empty or "year" not in df.columns:
        return df
    year_series = pd.to_numeric(df["year"], errors="coerce")
    return df[(year_series >= year_range[0]) & (year_series <= year_range[1])]


def run_single_notice_extraction(
    raw_text: str,
    legal_form: str,
    year: int,
    issue_number: int,
    source_file: str,
    friend_index: Dict[str, Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    cleaned = clean_text(raw_text)
    is_constitution = is_constitution_notice(cleaned)

    metadata = {
        "legal_form": legal_form,
        "year": int(year),
        "issue_number": int(issue_number),
        "source_file": source_file,
    }

    record = parse_notice(cleaned, metadata)

    enriched = 0
    if friend_index:
        reference = Path(source_file).stem
        enriched = apply_friend_fallback(record, cleaned, reference, friend_index)

    return {
        "cleaned_text": cleaned,
        "is_constitution": is_constitution,
        "record": record,
        "enriched_fields": enriched,
    }


def render_header() -> None:
    st.title("📄 JORT Extraction - Proof of Concept")
    st.caption(
        "Prototype interactif pour démontrer l'extraction structurée des annonces de constitution "
        "(Regex + NLP fallback + enrichissement Friend)."
    )
    st.info("Active dataset scope: years 2004-2014")


def render_sidebar() -> Dict[str, Any]:
    st.sidebar.header("Configuration")

    mode = st.sidebar.radio(
        "Mode",
        [
            "Tutor Presentation (Story Mode)",
            "Single Notice Demo",
            "Dataset Analytics",
            "Project Showcase",
        ],
    )

    default_output = str(PROJECT_ROOT / "output" / "extracted_notices.json")
    output_path = st.sidebar.text_input("Output JSON path", value=default_output)

    year_range = st.sidebar.slider(
        "Years in focus",
        min_value=YEAR_MIN,
        max_value=YEAR_MAX,
        value=(YEAR_MIN, YEAR_MAX),
        step=1,
    )

    use_friend = st.sidebar.checkbox("Enable Friend enrichment", value=False)
    default_friend = str(PROJECT_ROOT / "anonyme" / "2004")
    friend_dir = st.sidebar.text_input("Friend folder path", value=default_friend)

    friend_index: Dict[str, Dict[str, str]] = {}
    if use_friend:
        friend_index = load_friend_index_cached(friend_dir)
        if friend_index:
            st.sidebar.success(f"Friend index loaded: {len(friend_index)} references")
        else:
            st.sidebar.warning("Friend index not loaded (check path)")

    return {
        "mode": mode,
        "output_path": output_path,
        "year_range": year_range,
        "friend_index": friend_index,
    }


def _extract_first_section(markdown_text: str, max_lines: int = 14) -> str:
    if not markdown_text.strip():
        return "(No content found)"

    lines = [line.rstrip() for line in markdown_text.splitlines()]
    picked: List[str] = []
    started = False
    for line in lines:
        if line.strip().startswith("#") and started and len(picked) >= 6:
            break
        if line.strip():
            started = True
        if started:
            picked.append(line)
        if len(picked) >= max_lines:
            break
    return "\n".join(picked).strip() or "(No content found)"


def render_chapter_diagram(selected_step: str) -> None:
    st.markdown("### Visual Storyboard")

    base_style = """
    <style>
        .flow-wrap {
            border-radius: 16px;
            padding: 0.9rem;
            background: linear-gradient(140deg, #ffffff 0%, #f4faff 100%);
            border: 1px solid #dbeafe;
            margin-bottom: 0.7rem;
        }
        .flow-line {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.5rem;
        }
        .node {
            border-radius: 12px;
            padding: 0.45rem 0.65rem;
            background: #ffffff;
            border: 1px solid #cbd5e1;
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
            font-size: 0.88rem;
            font-weight: 600;
        }
        .node-blue { background: #e0f2fe; border-color: #7dd3fc; }
        .node-green { background: #dcfce7; border-color: #86efac; }
        .node-gold { background: #fef3c7; border-color: #fcd34d; }
        .node-rose { background: #ffe4e6; border-color: #fda4af; }
        .arrow { font-weight: 800; color: #334155; }
    </style>
    """

    diagram_html = ""

    if selected_step == "4) Solution & Conception":
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-gold">Raw JORT Notice</div>
                <div class="arrow">→</div>
                <div class="node node-blue">Encoding Fallback<br/>(utf-8/cp1252/latin-1)</div>
                <div class="arrow">→</div>
                <div class="node node-blue">OCR Cleaning</div>
            </div>
            <div class="flow-line" style="margin-top:0.5rem;">
                <div class="node node-green">Constitution Detector</div>
                <div class="arrow">→</div>
                <div class="node node-green">Regex Field Extractor</div>
                <div class="arrow">→</div>
                <div class="node node-green">Role Extractor<br/>(Manager/PDG/DG)</div>
            </div>
            <div class="flow-line" style="margin-top:0.5rem;">
                <div class="node node-rose">NLP Fallback<br/>(spaCy)</div>
                <div class="arrow">→</div>
                <div class="node node-rose">Friend Enrichment<br/>(optional)</div>
                <div class="arrow">→</div>
                <div class="node node-gold">Structured JSON</div>
            </div>
        </div>
        """
    elif selected_step == "2) Contexte & Problématique":
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-gold">Non-indexed PDFs</div>
                <div class="arrow">+</div>
                <div class="node node-gold">OCR Noise</div>
                <div class="arrow">+</div>
                <div class="node node-gold">Multi-columns</div>
            </div>
            <div class="flow-line" style="margin-top:0.5rem;">
                <div class="arrow">⇣</div>
                <div class="node node-rose">Manual processing not scalable</div>
                <div class="arrow">⇣</div>
                <div class="node node-blue">Need automated pipeline</div>
            </div>
        </div>
        """
    elif selected_step == "6) Méthodologie & Implémentation":
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-blue">cleaner.py</div>
                <div class="arrow">→</div>
                <div class="node node-blue">patterns.py</div>
                <div class="arrow">→</div>
                <div class="node node-blue">parser.py</div>
                <div class="arrow">→</div>
                <div class="node node-blue">nlp_enrichment.py</div>
                <div class="arrow">→</div>
                <div class="node node-blue">enrichment.py</div>
                <div class="arrow">→</div>
                <div class="node node-blue">filesystem.py</div>
            </div>
        </div>
        """
    elif selected_step == "7) Pipeline en action":
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-gold">Raw text</div>
                <div class="arrow">→</div>
                <div class="node node-green">Cleaned text</div>
                <div class="arrow">→</div>
                <div class="node node-green">Parsed fields</div>
                <div class="arrow">→</div>
                <div class="node node-rose">Fallback fill</div>
                <div class="arrow">→</div>
                <div class="node node-gold">JSON record</div>
            </div>
        </div>
        """
    elif selected_step == "9) NLP Governance":
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-blue">Governance block detection</div>
                <div class="arrow">→</div>
                <div class="node node-blue">Sentence segmentation</div>
                <div class="arrow">→</div>
                <div class="node node-green">NER PERSON extraction</div>
                <div class="arrow">→</div>
                <div class="node node-gold">Role assignment</div>
            </div>
        </div>
        """
    else:
        diagram_html = """
        <div class="flow-wrap">
            <div class="flow-line">
                <div class="node node-gold">Business Need</div>
                <div class="arrow">→</div>
                <div class="node node-blue">Technical Design</div>
                <div class="arrow">→</div>
                <div class="node node-green">Implementation</div>
                <div class="arrow">→</div>
                <div class="node node-rose">Validation</div>
                <div class="arrow">→</div>
                <div class="node node-gold">Impact</div>
            </div>
        </div>
        """

    components.html(base_style + diagram_html, height=240, scrolling=False)


def render_tutor_presentation(output_path: str, year_range: tuple[int, int]) -> None:
    st.subheader("Tutor Presentation - Story Mode")
    st.caption("Version narrative, visuelle et fun pour la restitution.")

    components.html(
        """
        <style>
            .stage-wrap {
                position: relative;
                overflow: hidden;
                border-radius: 18px;
            }
            .hero-box {
                background: linear-gradient(130deg, #fff7d6 0%, #eaf6ff 45%, #e9ffe9 100%);
                border: 1px solid #d9e8f5;
                border-radius: 18px;
                padding: 1.1rem 1.2rem;
                margin-bottom: 1rem;
                box-shadow: 0 10px 30px rgba(17, 24, 39, 0.08);
            }
            .shape-1 {
                width: 180px;
                height: 180px;
                border-radius: 50%;
                position: absolute;
                top: -55px;
                right: -45px;
                background: rgba(111, 214, 255, 0.26);
            }
            .shape-2 {
                width: 120px;
                height: 120px;
                border-radius: 28px;
                position: absolute;
                bottom: -38px;
                left: -24px;
                background: rgba(255, 198, 90, 0.30);
                transform: rotate(18deg);
            }
            .fun-note {
                background: #f8fff4;
                border-left: 5px solid #76b947;
                padding: 0.7rem 0.9rem;
                border-radius: 6px;
                margin: 0.4rem 0 0.9rem 0;
            }
            .timeline-chip {
                display: inline-block;
                padding: 0.25rem 0.6rem;
                border-radius: 999px;
                background: #1f2937;
                color: #f9fafb;
                font-size: 0.8rem;
                margin-right: 0.35rem;
            }
        </style>
        """,
        height=0,
        scrolling=False,
    )

    components.html(
        """
        <div class="stage-wrap">
            <div class="hero-box">
                <div class="shape-1"></div>
                <div class="shape-2"></div>
                <h3 style="margin:0;">From Chaos to JSON: the JORT Adventure</h3>
                <p style="margin:0.45rem 0 0 0;">
                    2004 → 2014: Des PDF bruyants, des colonnes OCR capricieuses...
                    puis un pipeline robuste orienté intelligence économique.
                </p>
            </div>
        </div>
        """,
        height=190,
        scrolling=False,
    )

    components.html(
        """
        <span class="timeline-chip">2004</span>
        <span class="timeline-chip">...</span>
        <span class="timeline-chip">2014</span>
        """,
        height=35,
        scrolling=False,
    )

    with st.expander("Warm-up: 20-second elevator pitch", expanded=True):
        st.markdown(
            """
            - **Problème**: les annonces légales JORT sont riches mais non structurées.
            - **Solution**: pipeline hybride **Regex + NLP + Friend enrichment**.
            - **Résultat**: JSON exploitable pour intelligence économique sur 2004-2014.
            """
        )

    components.html(
        '<div class="fun-note">Plot twist: OCR says "I tried my best". Regex says "challenge accepted".</div>',
        height=55,
        scrolling=False,
    )

    # Stage navigator
    story_steps = [
        "1) Entreprise & Vision",
        "2) Contexte & Problématique",
        "3) Étude de l'existant",
        "4) Solution & Conception",
        "5) Besoin & Technologies",
        "6) Méthodologie & Implémentation",
        "7) Pipeline en action",
        "8) Patterns Regex",
        "9) NLP Governance",
        "10) Validation Friend",
        "11) État d'avancement",
    ]
    selected_step = st.selectbox("Story chapter", story_steps, index=0)

    render_chapter_diagram(selected_step)

    chapter_files = {
        "1) Entreprise & Vision": PROJECT_ROOT / "docs" / "1_ENTREPRISE.md",
        "2) Contexte & Problématique": PROJECT_ROOT / "docs" / "2_CONTEXTE_PROBLEMATIQUE.md",
        "3) Étude de l'existant": PROJECT_ROOT / "docs" / "3_ETUDE_EXISTANT.md",
        "4) Solution & Conception": PROJECT_ROOT / "docs" / "4_SOLUTION_CONCEPTION.md",
        "5) Besoin & Technologies": PROJECT_ROOT / "docs" / "5_ANALYSE_BESOIN_TECH.md",
        "6) Méthodologie & Implémentation": PROJECT_ROOT / "docs" / "6_METHODOLOGIE_IMPLEMENTATION.md",
        "7) Pipeline en action": PROJECT_ROOT / "docs" / "7_EXTRACTION_PIPELINE.md",
        "8) Patterns Regex": PROJECT_ROOT / "docs" / "8_PATTERN_EXTRACTION.md",
        "9) NLP Governance": PROJECT_ROOT / "docs" / "9_GOVERNANCE_NLP.md",
        "10) Validation Friend": PROJECT_ROOT / "docs" / "10_ENRICHMENT_VALIDATION.md",
        "11) État d'avancement": PROJECT_ROOT / "docs" / "11_ETAT_AVANCEMENT.md",
    }

    markdown_text = load_markdown_file(str(chapter_files[selected_step]))
    chapter_preview = _extract_first_section(markdown_text)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("### Chapter snapshot")
        st.markdown(chapter_preview)
    with right:
        st.markdown("### Presenter cues")
        quick_cues = {
            "1) Entreprise & Vision": [
                "Présenter Infyntra en 2 phrases max.",
                "Relier immédiatement au besoin économique.",
            ],
            "2) Contexte & Problématique": [
                "Insister sur les PDF non-indexés + OCR bruité.",
                "Montrer pourquoi le manuel n'est pas scalable.",
            ],
            "3) Étude de l'existant": [
                "Expliquer ce qui existait et ce qui manquait.",
                "Valoriser les découvertes techniques terrain.",
            ],
            "4) Solution & Conception": [
                "Raconter la chaîne en 6 étapes.",
                "Faire le lien avec ton implémentation réelle.",
            ],
            "5) Besoin & Technologies": [
                "Montrer les 12 champs extraits.",
                "Justifier Regex + NLP comme choix pragmatique.",
            ],
            "6) Méthodologie & Implémentation": [
                "Passer module par module (cleaner, parser, enrichment).",
                "Montrer 1 snippet clé par module.",
            ],
            "7) Pipeline en action": [
                "Faire un before/after d'une notice.",
                "Montrer où chaque fallback intervient.",
            ],
            "8) Patterns Regex": [
                "Donner 2 exemples de patterns robustes.",
                "Expliquer les cas limites capital/manager.",
            ],
            "9) NLP Governance": [
                "Présenter le gain de recall sur leadership.",
                "Expliquer rapidement NER + lemmatisation.",
            ],
            "10) Validation Friend": [
                "Montrer comment tu réduis les faux positifs.",
                "Valoriser la logique d'alignement avec le texte source.",
            ],
            "11) État d'avancement": [
                "Donner KPI actuels, puis roadmap.",
                "Terminer par impacts business concrets.",
            ],
        }
        for cue in quick_cues.get(selected_step, []):
            st.write(f"- {cue}")

    st.markdown("### Evidence board")
    records = load_json_records(output_path)
    if records:
        df = filter_df_by_year_range(records_to_dataframe(records), year_range)
        if df.empty:
            st.warning("No records available for the selected year range.")
            return

        core_fields = [
            "company_name",
            "capital",
            "address",
            "corporate_purpose",
            "duration",
            "manager",
        ]
        missing_df = compute_missing_stats(df, core_fields)
        completion = 100.0 - float(missing_df["missing_rate"].mean())

        m1, m2, m3 = st.columns(3)
        m1.metric("Parsed records", len(df))
        m2.metric("Estimated core completeness", f"{completion:.2f}%")
        m3.metric("Legal forms", int(df["legal_form"].nunique()) if "legal_form" in df.columns else 0)

        chart_left, chart_right = st.columns([1, 1])
        with chart_left:
            st.markdown("#### Records by year")
            if "year" in df.columns:
                year_counts = (
                    pd.to_numeric(df["year"], errors="coerce")
                    .dropna()
                    .astype(int)
                    .value_counts()
                    .sort_index()
                )
                year_counts_df = year_counts.rename_axis("year").reset_index(name="count")
                year_counts_df["year"] = year_counts_df["year"].astype(str)
                st.bar_chart(year_counts_df.set_index("year"))
        with chart_right:
            st.markdown("#### Legal forms by year")
            if "year" in df.columns and "legal_form" in df.columns:
                pivot = (
                    df.assign(year=pd.to_numeric(df["year"], errors="coerce"))
                    .dropna(subset=["year"])
                    .assign(year=lambda x: x["year"].astype(int))
                    .pivot_table(index="year", columns="legal_form", aggfunc="size", fill_value=0)
                    .sort_index()
                )
                if not pivot.empty:
                    st.bar_chart(pivot)

        st.dataframe(missing_df, width="stretch", hide_index=True)
    else:
        st.info("No dataset loaded yet. Run the pipeline to unlock metrics on this page.")

    st.markdown("### Key narrative line")
    st.info(
        "On 2004-2014, the design is intentionally layered: deterministic regex for speed, NLP fallback for noisy cases, and Friend alignment for safer completion."
    )

    with st.expander("Open full markdown source for this chapter"):
        st.markdown(markdown_text if markdown_text else "(No markdown content)")


def render_project_showcase() -> None:
    st.subheader("Project Showcase")

    c1, c2, c3 = st.columns(3)
    c1.metric("Pipeline", "Regex + NLP")
    c2.metric("Output", "Structured JSON")
    c3.metric("Scope", "Constitution Notices 2004-2014")

    st.markdown("### Workflow map")
    components.html(
        """
        <div style="border:1px solid #cbd5e1;border-radius:14px;padding:0.9rem;background:linear-gradient(120deg,#f8fbff,#eefcf3)">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                <span style="padding:6px 10px;border-radius:10px;background:#fef3c7;border:1px solid #fcd34d;font-weight:600">Collect</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#e0f2fe;border:1px solid #7dd3fc;font-weight:600">Clean</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#dcfce7;border:1px solid #86efac;font-weight:600">Extract</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#ffe4e6;border:1px solid #fda4af;font-weight:600">Enrich</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#fef3c7;border:1px solid #fcd34d;font-weight:600">Deliver JSON</span>
            </div>
        </div>
        """,
        height=90,
        scrolling=False,
    )

    st.markdown("### Pipeline flow")
    st.markdown(
        """
        1. Lecture du texte brut (multi-encodage)
        2. Nettoyage OCR
        3. Détection constitution vs non-constitution
        4. Extraction regex des champs clés
        5. Fallback NLP pour champs manquants
        6. Enrichissement Friend (optionnel)
        7. Structuration JSON
        """
    )

    st.markdown("### Champs extraits")
    st.write(
        [
            "company_name",
            "legal_form",
            "capital",
            "address",
            "corporate_purpose",
            "duration",
            "manager",
            "president_directeur_general",
            "president",
            "directeur_general",
            "administrators",
            "auditor",
            "year",
            "issue_number",
            "source_file",
            "not_applicable_fields",
        ]
    )


def render_single_notice_demo(friend_index: Dict[str, Dict[str, str]]) -> None:
    st.subheader("Single Notice Demo")

    st.markdown("### Extraction storyboard")
    components.html(
        """
        <div style="border:1px solid #cbd5e1;border-radius:14px;padding:0.8rem;background:linear-gradient(125deg,#fff7d6,#eaf6ff)">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                <span style="padding:5px 10px;border-radius:999px;background:#1f2937;color:#fff">Input Text</span>
                <b>→</b>
                <span style="padding:5px 10px;border-radius:999px;background:#1f2937;color:#fff">Clean</span>
                <b>→</b>
                <span style="padding:5px 10px;border-radius:999px;background:#1f2937;color:#fff">Detect Constitution</span>
                <b>→</b>
                <span style="padding:5px 10px;border-radius:999px;background:#1f2937;color:#fff">Parse + NLP</span>
                <b>→</b>
                <span style="padding:5px 10px;border-radius:999px;background:#1f2937;color:#fff">JSON</span>
            </div>
        </div>
        """,
        height=80,
        scrolling=False,
    )

    with st.expander("Input metadata", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        legal_form = col1.selectbox("Legal form", ["anonyme", "sarl", "suarl", "autre"], index=0)
        year = col2.number_input("Year", min_value=YEAR_MIN, max_value=YEAR_MAX, value=2010, step=1)
        issue_number = col3.number_input("Issue number", min_value=1, max_value=999, value=1, step=1)
        source_file = col4.text_input("Source file", value="demo-constitution.txt")

    st.markdown("Paste notice text or upload a .txt file")
    uploaded_file = st.file_uploader("Upload .txt notice", type=["txt"])

    default_text = (
        "Avis de constitution\n\n"
        "Dénomination: TECH SOLUTIONS SARL\n"
        "Siège social: 123 Rue de Carthage, Tunis\n"
        "Capital social: 50000 DT\n"
        "Objet social: Développement de logiciels\n"
        "Durée: 99 ans\n"
        "Gérant: M. Ahmed Ben Ali\n"
    )

    raw_text = st.text_area("Notice text", value=default_text, height=280)

    if uploaded_file is not None:
        raw_text = uploaded_file.read().decode("utf-8", errors="replace")
        st.info("Uploaded file loaded into input")

    run = st.button("Run Extraction", type="primary")
    if not run:
        return

    if not raw_text.strip():
        st.error("Please provide notice text before running extraction.")
        return

    with st.spinner("Parsing notice..."):
        result = run_single_notice_extraction(
            raw_text=raw_text,
            legal_form=legal_form,
            year=int(year),
            issue_number=int(issue_number),
            source_file=source_file,
            friend_index=friend_index,
        )

    record = result["record"]
    extracted_fields = [
        "company_name",
        "capital",
        "address",
        "corporate_purpose",
        "duration",
        "manager",
        "president_directeur_general",
        "president",
        "directeur_general",
        "administrators",
        "auditor",
    ]
    completeness = compute_record_completeness(record, extracted_fields)

    m1, m2, m3 = st.columns(3)
    m1.metric("Is Constitution", "Yes" if result["is_constitution"] else "No")
    m2.metric("Record Completeness", f"{completeness}%")
    m3.metric("Friend Enriched Fields", result["enriched_fields"])

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("### Extracted JSON")
        st.json(record)
        st.download_button(
            label="Download JSON",
            data=json.dumps(record, ensure_ascii=False, indent=2),
            file_name=f"{Path(source_file).stem}_extracted.json",
            mime="application/json",
        )

    with col_b:
        st.markdown("### Cleaned Text")
        st.text_area("cleaned_text", value=result["cleaned_text"], height=320, label_visibility="collapsed")

    st.markdown("### Field Status")
    status_rows = []
    for field in extracted_fields:
        status_rows.append(
            {
                "field": field,
                "value": record.get(field),
                "status": "present" if record.get(field) not in (None, "") else "missing",
            }
        )
    st.dataframe(pd.DataFrame(status_rows), width="stretch", hide_index=True)


def render_dataset_analytics(output_path: str, year_range: tuple[int, int]) -> None:
    st.subheader("Dataset Analytics")

    st.markdown("### Analytics workflow")
    components.html(
        """
        <div style="border:1px solid #cbd5e1;border-radius:14px;padding:0.8rem;background:linear-gradient(125deg,#f3faff,#f0fff7)">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                <span style="padding:6px 10px;border-radius:10px;background:#dbeafe;border:1px solid #93c5fd;font-weight:600">Load JSON</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#dcfce7;border:1px solid #86efac;font-weight:600">Filter Years</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#fef3c7;border:1px solid #fcd34d;font-weight:600">Compute KPIs</span>
                <b>→</b>
                <span style="padding:6px 10px;border-radius:10px;background:#ffe4e6;border:1px solid #fda4af;font-weight:600">Charts + CSV</span>
            </div>
        </div>
        """,
        height=80,
        scrolling=False,
    )

    records = load_json_records(output_path)
    if not records:
        st.warning("No records found. Run the pipeline first or check the output JSON path.")
        return

    df = filter_df_by_year_range(records_to_dataframe(records), year_range)
    if df.empty:
        st.warning("No records available for the selected year range.")
        return

    st.success(f"Loaded {len(df)} records for years {year_range[0]}-{year_range[1]}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records", len(df))
    c2.metric("Legal forms", int(df["legal_form"].nunique()) if "legal_form" in df.columns else 0)
    c3.metric("Years", int(df["year"].nunique()) if "year" in df.columns else 0)
    c4.metric("Issues", int(df["issue_number"].nunique()) if "issue_number" in df.columns else 0)

    if "year" in df.columns:
        st.markdown("### Records per year")
        by_year = (
            pd.to_numeric(df["year"], errors="coerce")
            .dropna()
            .astype(int)
            .value_counts()
            .sort_index()
        )
        by_year_df = by_year.rename_axis("year").reset_index(name="count")
        by_year_df["year"] = by_year_df["year"].astype(str)
        st.line_chart(by_year_df.set_index("year"))

    st.markdown("### Records by legal form")
    if "legal_form" in df.columns:
        by_form = df["legal_form"].value_counts().rename_axis("legal_form").reset_index(name="count")
        st.bar_chart(by_form.set_index("legal_form"))
        st.dataframe(by_form, width="stretch", hide_index=True)

    if "year" in df.columns and "legal_form" in df.columns:
        st.markdown("### Year x legal form matrix")
        matrix = (
            df.assign(year=pd.to_numeric(df["year"], errors="coerce"))
            .dropna(subset=["year"])
            .assign(year=lambda x: x["year"].astype(int))
            .pivot_table(index="year", columns="legal_form", aggfunc="size", fill_value=0)
            .sort_index()
        )
        st.dataframe(matrix, width="stretch")

    st.markdown("### Missing-field analysis")
    core_fields = [
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
    ]
    missing_df = compute_missing_stats(df, core_fields)
    st.dataframe(missing_df, width="stretch", hide_index=True)

    st.markdown("### Preview")
    st.dataframe(df.head(50), width="stretch")

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download analytics CSV",
        data=csv_data,
        file_name="jort_extraction_preview.csv",
        mime="text/csv",
    )


def main() -> None:
    render_header()
    cfg = render_sidebar()

    mode = cfg["mode"]
    if mode == "Tutor Presentation (Story Mode)":
        render_tutor_presentation(cfg["output_path"], cfg["year_range"])
    elif mode == "Project Showcase":
        render_project_showcase()
    elif mode == "Single Notice Demo":
        render_single_notice_demo(cfg["friend_index"])
    else:
        render_dataset_analytics(cfg["output_path"], cfg["year_range"])


if __name__ == "__main__":
    main()
