# ⚖️ MetaLex — Legal Metrology Compliance Checker

> **Smart India Hackathon (SIH) 2026 — Team 26034**
>
> Scan a product label → AI reads it → Rules decide compliance → Officer reviews → PDF report generated.

---

## What is MetaLex?

MetaLex is a web application that helps government enforcement officers check whether packaged products comply with the **Legal Metrology (Packaged Commodities) Rules, 2011**. You simply upload a photo of a product label, and the system automatically:

1. Reads all the text on the label using **AI (Google Gemini + EasyOCR)**
2. Checks it against **28 legal rules** (MRP, net quantity, manufacturer details, etc.)
3. Gives a **COMPLIANT / NON-COMPLIANT / NEEDS REVIEW** verdict
4. Shows exactly which fields passed or failed, with bounding boxes on the image
5. Generates an **official PDF compliance report**

> **"AI extracts. Deterministic rules decide. Evidence explains. Human reviews uncertainty."**

---

## How to Run Locally

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Step 1 — Clone and set up Python environment

```bash
git clone https://github.com/asadulla-cp/SIH_26034.git
cd SIH_26034

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Step 2 — Add your Gemini API key

Create a `.env` file in the project root:

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Step 3 — Start the backend

```bash
# From the project root
PYTHONPATH=. .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4 — Start the frontend (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

### Open the app

| Service | URL |
|---|---|
| Web UI | http://localhost:5173 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

---

## Quick Start (One Command)

If you just want to run everything at once:

```bash
./run.sh
```

---

## Docker

```bash
cd docker
docker compose up --build
```

UI available at http://localhost:8080

---

## Demo Credentials

| Field | Value |
|---|---|
| Username | `demo_officer` |
| Password | `demo123` |

You can also register a new account from the login page.

---

## Demo Flow (for Judges)

1. Open the app → you'll land on the **Dashboard** with summary stats and recent inspections.
2. Go to **Scan Product** → upload any product image or use a demo sample.
3. Watch the pipeline run: preprocessing → Gemini extraction → rule engine → verdict.
4. Open an inspection result:
   - See which fields **PASS** (green) or **FAIL** (red)
   - Click a field to highlight its **bounding box** on the image
   - Use **Approve / Reject / Edit** to manually review uncertain fields
5. Go to **Reports** → download the official PDF.
6. Open **Compliance Map** to see geo-tagged inspections across India.

---

## How It Works

```
Photo of product label
        │
        ▼
   Image preprocessing
   (denoise, contrast enhancement, blur detection)
        │
        ▼
   Google Gemini 2.5 Flash (multimodal AI)
   + EasyOCR (bounding box evidence)
        │
        ▼
   Structured field extraction
   (product name, MRP, net quantity, manufacturer,
    date, consumer care, country of origin, barcode)
        │
        ▼
   Deterministic Rule Engine
   (28 rules from Legal Metrology PC Rules, 2011)
        │
        ▼
   COMPLIANT / NON-COMPLIANT / NEEDS REVIEW
   + violation explanations + bounding boxes
        │
        ▼
   SQLite database → PDF report
```

### Why both Gemini and EasyOCR?

- **Gemini** understands context — it can read curved text, complex layouts, and mixed languages.
- **EasyOCR** gives us exact pixel bounding boxes so we can highlight fields on the image.
- If Gemini is unavailable (no API key), EasyOCR runs as a standalone fallback.

### Why deterministic rules (not AI) for compliance decisions?

Legal decisions must be auditable and reproducible. AI can hallucinate. The rule engine always produces the same output for the same input — no randomness, full transparency.

---

## Features

### Scanning
- Upload 1–5 images of the same product (different angles)
- Live camera scan (mobile-friendly)
- Demo sample images for quick testing

### Compliance Checks (28 Rules)
| Rule ID | What it checks |
|---|---|
| LM-PC-001 | Product name present and legible |
| LM-PC-002 | Net quantity in standard metric units (g, kg, ml, L) |
| LM-PC-003 | MRP declared in ₹, inclusive of all taxes |
| LM-PC-004 | Manufacturer / packer / importer name and address |
| LM-PC-005 | Consumer care phone number or email |
| LM-PC-006 | Manufacturing / packing / import date |
| LM-PC-007 | Country of origin (required for imported goods) |
| LM-PC-FS-* | Font size compliance for MRP and net quantity |
| LM-PC-BC-* | Barcode verification against GS1 registry |
| … and more | See `rules/rules.json` for full list |

### Smart Review System
- **NEEDS REVIEW** triggers when OCR confidence is below 60% — the system never auto-fails a product it can't read clearly
- Officers can **Approve**, **Reject**, or **Edit** any field
- All officer actions are saved to an audit trail

### Reports & Analytics
- Official PDF compliance report with inspection ID and legal disclaimer
- Executive dashboard with violation trends
- Geo-tagged compliance map (Leaflet.js) showing inspections across India
- Legal notice generator (PDF) for enforcement action

### Authentication
- JWT-based login with bcrypt password hashing
- Each inspection is linked to the officer who performed it
- Personal inspection history per user

---

## Project Structure

```
SIH_26034/
├── backend/
│   ├── main.py                  ← FastAPI app, all API endpoints
│   ├── database.py              ← SQLite connection (PostgreSQL-ready)
│   ├── auth.py                  ← JWT authentication
│   ├── models/
│   │   └── db_models.py         ← Database schema
│   └── services/
│       ├── ocr_pipeline.py      ← EasyOCR + image preprocessing
│       ├── gemini_pipeline.py   ← Google Gemini 2.5 Flash integration
│       ├── report_service.py    ← PDF report generator (ReportLab)
│       ├── legal_notice_generator.py ← Enforcement notice PDFs
│       ├── barcode_detector.py  ← Barcode reading + GS1 verification
│       ├── font_analyzer.py     ← Font size measurement in mm
│       └── anomaly_detector.py  ← Image manipulation detection
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── Dashboard.tsx         ← Stats, trends, quick actions
│       │   ├── ScanProduct.tsx       ← Main scan screen
│       │   ├── InspectionDetail.tsx  ← Per-inspection deep dive
│       │   ├── InspectionHistory.tsx ← Searchable audit log
│       │   ├── ComplianceMap.tsx     ← Geo map of inspections
│       │   ├── RuleLibrary.tsx       ← All 28 rules with citations
│       │   └── Settings.tsx          ← Diagnostics and config
│       ├── api.ts               ← All API calls
│       └── types.ts             ← TypeScript interfaces
├── rules/
│   ├── rules.json               ← All 28 legal rules (edit to update)
│   └── rule_engine.py           ← Deterministic compliance engine
├── demo/
│   └── sample_images/           ← Test product label images
├── tests/                       ← Pytest unit + integration tests
├── docker/                      ← Docker setup
├── run.sh                       ← One-command launcher
└── requirements.txt
```

---

## API Reference

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/api/health` | System health and OCR engine status |
| POST | `/api/scan` | Scan product images (multipart, field: `files`) |
| GET | `/api/inspections` | List all inspections |
| GET | `/api/inspections/{id}` | Get single inspection details |
| POST | `/api/inspections/{id}/review` | Submit officer review action |
| GET | `/api/inspections/geo` | Geo-tagged inspections for map |
| GET | `/api/dashboard/stats` | Dashboard summary statistics |
| GET | `/api/reports/{id}` | Download PDF report |
| GET | `/api/rules` | All rules in JSON |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/notices` | List generated legal notices |

Full interactive docs: http://localhost:8000/docs

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Recommended | Google Gemini API key. Get one free at [aistudio.google.com](https://aistudio.google.com). Without it, EasyOCR is used as fallback. |
| `DATABASE_URL` | No | Defaults to SQLite. Set to a PostgreSQL URL for production. |
| `DEBUG_MODE` | No | Set to `true` for verbose logging. |

---

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

---

## Known Limitations

- **Curved labels** (cans, bottles) — text on curved surfaces may have lower OCR accuracy. Use multiple angles.
- **Handwritten labels** — not supported.
- **Languages** — English and Indian numeric formats are fully supported. Hindi/regional script support is partial via EasyOCR.
- **Rules are prototype mappings** — the `rules.json` is modeled after the Legal Metrology (PC) Rules, 2011 but has not been officially certified by a government authority.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| AI / Vision | Google Gemini 2.5 Flash, EasyOCR, OpenCV |
| Frontend | React 19, TypeScript, Vite, Leaflet.js, Lucide icons |
| Database | SQLite (dev) / PostgreSQL (prod) |
| PDF generation | ReportLab |
| Auth | JWT + bcrypt |
| Deployment | Docker, Uvicorn |

---

## License

Built for Smart India Hackathon 2026. Prototype — not for official enforcement use.
