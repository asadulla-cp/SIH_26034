# ⚖️ MetaLex — Quick Start Guide

> **Smart India Hackathon 2026 · Legal Metrology Compliance Checking System**
> Automated verification of packaged-commodity declarations under the Legal Metrology (Packaged Commodities) Rules, 2011.

---

## Prerequisites

| Tool | Minimum Version | Check |
|------|----------------|-------|
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

---

## 1. Clone & Enter the Project

```bash
git clone <repo-url>
cd SIH_26034
```

---

## 2. One-Command Start (Recommended)

```bash
./run.sh
```

This single script:
- Installs missing Python dependencies automatically
- Starts the **FastAPI backend** on port `8000`
- Starts the **Vite React frontend** on port `5173`
- Press `Ctrl+C` to stop both servers

---

## 3. Manual Start (Two Terminals)

### Terminal 1 — Backend

```bash
# Install Python dependencies (first time only)
pip3 install fastapi uvicorn python-dotenv reportlab pillow opencv-python \
             sqlalchemy pydantic easyocr python-multipart aiofiles jinja2 \
             "python-jose[cryptography]==3.3.0" "passlib[bcrypt]==1.7.4" bcrypt==4.0.1

# Start the API server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Frontend

```bash
cd frontend

# Install npm packages (first time only)
npm install

# Start the dev server
npm run dev
```

---

## 4. Open the App

| URL | Description |
|-----|-------------|
| http://localhost:5173 | **Web UI** — Enforcement Dashboard |
| http://localhost:8000/docs | **Swagger API Docs** (interactive) |
| http://localhost:8000/api/health | Backend health check (JSON) |

---

## 5. First Login

Authentication is required. Create an account on first launch.

1. Open **http://localhost:5173** → you land on the **Login** page
2. Click the **Register** tab
3. Fill in username, email, and password (min 6 characters)
4. Click **Create Account** — you're logged in immediately
5. To log out, click **Sign Out** at the bottom of the sidebar

> **Demo credentials** (if seeded): there are no pre-seeded accounts — register your own in seconds.

---

## 6. Run a Demo Inspection (Judges)

Once logged in, the fastest way to see the system in action:

### From the Dashboard
Click any of the three preset buttons in the **Instant Demo Presets** panel:

| Button | Expected Result |
|--------|----------------|
| ✅ 1. Fully Compliant Package | Score **100/100** · 0 violations |
| ❌ 2. Missing MRP Declaration | Score **~82/100** · Rule `LM-PC-004` FAIL |
| ⚠️ 3. Ambiguous / Low OCR Confidence | Status **NEEDS REVIEW** · OCR confidence 42% |

### Upload a Real Image
1. Go to **Scan Product** in the sidebar
2. Drag-and-drop or click to upload any package label image (JPG/PNG, max 20 MB)
3. Watch the live OCR pipeline extract fields and the rule engine validate them
4. View bounding boxes, field declarations, and violation explanations

### Download an Enforcement Report
On any completed inspection → click **Download PDF Report** for an official multi-page compliance report with inspection ID and legal disclaimer.

---

## 7. Rule Library

Navigate to **Rule Library** to browse all **22 deterministic rules** (v2.0.0):

- Search by rule ID, title, or keyword
- Filter by **severity** (High / Medium / Low) or **category**
- Expand any rule to see: requirement, legal basis, penalty, exemptions, and amendment notes
- Categories covered:
  - Mandatory Declarations (Rule 6)
  - Quantity & Measurement (Rules 11–13, Schedules II–IV)
  - MRP & Pricing (Rule 2(m), 6(1)(e), 18)
  - Display & Visibility (Rules 7–9)
  - Exemptions (Rules 3, 26)
  - Wholesale & Import (Rules 24–25)

---

## 8. Run Tests

```bash
python3 -m pytest tests/ -v
```

Expected: **31 tests passing** in ~1.5 s.

---

## 9. Project Structure (Key Files)

```
SIH_26034/
├── run.sh                          # One-command launcher
├── requirements.txt                # Python dependencies
│
├── backend/
│   ├── main.py                     # FastAPI app + all API endpoints
│   ├── auth.py                     # JWT auth (register / login / me)
│   ├── database.py                 # SQLite connection (PostgreSQL-ready)
│   ├── models/db_models.py         # SQLAlchemy models incl. User
│   └── services/
│       ├── ocr_pipeline.py         # EasyOCR + CLAHE preprocessing
│       ├── demo_service.py         # Pre-built demo datasets
│       └── report_service.py       # ReportLab PDF generator
│
├── rules/
│   ├── rules.json                  # 22 versioned rules (v2.0.0)
│   └── rule_engine.py              # Deterministic validator (no LLM)
│
├── frontend/
│   └── src/
│       ├── App.tsx                 # Router + sidebar + protected routes
│       ├── AuthContext.tsx         # Login state (JWT in localStorage)
│       ├── Login.tsx               # Login / Register page
│       ├── api.ts                  # All API client functions
│       ├── types.ts                # TypeScript domain models
│       └── views/
│           ├── Dashboard.tsx       # KPIs + rules summary + demo presets
│           ├── ScanProduct.tsx     # Image upload + live OCR scan
│           ├── InspectionHistory.tsx
│           ├── InspectionDetail.tsx
│           ├── RuleLibrary.tsx     # Grouped rules + search/filter
│           └── Settings.tsx
│
├── tests/
│   ├── test_rule_engine.py         # 26 unit tests
│   └── test_api_e2e.py             # 5 end-to-end tests
│
└── demo/
    └── sample_images/              # Synthetic package label images
```

---

## 10. Environment Variables (Optional)

Create a `.env` file in the project root to override defaults:

```env
# JWT secret — CHANGE THIS in any non-demo deployment
JWT_SECRET_KEY=metalex-sih-secret-key-change-in-production

# Token expiry in minutes (default: 60)
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Gemini Vision API key (optional — enables Gemini OCR pipeline)
GEMINI_API_KEY=your_gemini_api_key_here

# Custom API base URL for the frontend (default: http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

---

## 11. Common Issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip3 install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'dotenv'` | Run `pip3 install python-dotenv` |
| Port 8000 already in use | `lsof -ti:8000 \| xargs kill` |
| Port 5173 already in use | `lsof -ti:5173 \| xargs kill` |
| Frontend shows "Backend Disconnected" | Ensure backend is running on port 8000 |
| Login fails after restart | Token is still valid — try logging out and back in |
| EasyOCR slow on first run | It downloads ~100 MB of model weights on first use — wait ~30 s |

---

## 12. Architecture in One Line

```
IMAGE → PREPROCESSING → EasyOCR → FIELD EXTRACTION → RULE ENGINE (22 rules) → VERDICT → PDF REPORT
```

**"AI extracts. Deterministic rules decide. Evidence explains. Human reviews uncertainty."**

---

*Legal Metrology (Packaged Commodities) Rules, 2011 — GSR 202(E) · SIH26034 Prototype · Not for production enforcement without legal verification.*
