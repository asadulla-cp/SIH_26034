# MetaLex

Prototype for **Smart India Hackathon**: software to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 by scanning product images and labels.

**AI extracts. Deterministic rules decide. Evidence explains. Human reviews uncertainty.**

This is a working local prototype. The rule pack is a **versioned prototype mapping**, not official gazette text.

## Start (local)

From the project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python demo/generate_samples.py

# Terminal 1 — API
cd backend
PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — UI
cd frontend
npm install
npm run dev
```

- UI: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

No login is required. Optional presentation credentials (not enforced): officer `ML-OFF-001` / `metalex2026`.

## Docker

```bash
cd docker
docker compose up --build
```

UI: http://127.0.0.1:8080

## Demo flow (judges)

1. Open the UI → **Dashboard** (seeded sample inspections).
2. **Scan Product** → click **Fully compliant atta pack** → expect COMPLIANT and boxes on the label.
3. Run **Missing MRP** → NON-COMPLIANT, MRP FAIL, evidence “Not detected in supplied image.”
4. Run **Missing consumer care** → FAIL on consumer care.
5. Run **Poor OCR / ambiguous MRP** → NEEDS REVIEW (do not auto-fail on low OCR confidence).
6. Run **Multiple violations** → several FAILs including imported origin.
7. Open a field to highlight its bounding box. Use Approve / Reject / Edit on review items.
8. **Reports** → download PDF.

## Design

- `rules/rules.json` — swap this file to update legal mappings.
- OCR: RapidOCR/Tesseract if installed; otherwise **demo fixtures** + graceful fallback (NEEDS REVIEW, no crash).
- SQLite at `backend/data/metalex.db` (PostgreSQL-ready SQLAlchemy models).
