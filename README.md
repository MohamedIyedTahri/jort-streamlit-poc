# JORT Streamlit Proof of Concept

Interactive Streamlit app for presenting the JORT extraction pipeline (2004-2014), including:
- Story-mode presentation with workflow diagrams
- Single notice live extraction demo
- Dataset analytics by year/legal form

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open https://share.streamlit.io/
3. Create new app:
   - Repository: `<your-user>/jort-streamlit-poc`
   - Branch: `main`
   - Main file path: `app.py`
4. Deploy.

## Repo structure

- `app.py`: entrypoint for deployment
- `docs/streamlit_app.py`: main app code
- `docs/*.md`: presentation content source
- `extractor/`, `utils/`: extraction logic
- `output/extracted_notices.json`: dataset sample (if present)
