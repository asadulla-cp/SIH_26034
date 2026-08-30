# ⚖️ MetaLex — Legal Metrology Compliance Checking System
> **Smart India Hackathon (SIH) 36-Hour Working Prototype**
> Automated compliance verification of packaged commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images, and labels.

---

## 🎯 Core Concept & Design Principle
```
IMAGE ➔ PREPROCESSING ➔ OCR / VISION ➔ STRUCTURED FIELD EXTRACTION ➔ DETERMINISTIC LEGAL RULE ENGINE ➔ COMPLIANCE VERDICT ➔ VISUAL EVIDENCE ➔ OFFICIAL PDF REPORT
```

**"AI extracts. Deterministic rules decide. Evidence explains. Human reviews uncertainty."**

---

## 🚀 1. Quickstart (How to Run)

### Option A: One-Command Runner (Recommended)
From the project root:
```bash
./run.sh
```
This automatically starts both the FastAPI backend (`http://localhost:8000`) and the Vite React frontend (`http://localhost:5173`).

### Option B: Manual Execution

1. **Start Backend Server:**
```bash
# In terminal 1 (project root):
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **Start Frontend Dev Server:**
```bash
# In terminal 2:
cd frontend
npm run dev
```

---

## 🌐 2. Localhost URLs & Endpoints
* **Web UI (Enforcement Dashboard):** [http://localhost:5173](http://localhost:5173)
* **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check Endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🔑 3. Test Credentials
* **Authentication:** Frictionless inspection mode enabled for hackathon demo. No login required.
* **Role Simulation:** Officer-level enforcement & review permissions active by default.

---

## 📂 4. Project Structure
```
metalex/
├── backend/
│   ├── api/
│   ├── core/
│   ├── models/
│   │   └── db_models.py       # SQLAlchemy database schema (Inspections, Violations, Reviews)
│   ├── services/
│   │   ├── ocr_pipeline.py    # CLAHE, Denoise, EasyOCR, regex/spatial heuristics
│   │   ├── demo_service.py    # Zero-network demo datasets for judge demo flow
│   │   └── report_service.py  # ReportLab official PDF compliance report generator
│   ├── database.py            # SQLite local connection (PostgreSQL compatible)
│   └── main.py                # FastAPI endpoints & static file serving
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Dashboard.tsx          # Executive enforcement dashboard & violation trends
│   │   │   ├── ScanProduct.tsx        # Flagship inspection screen with interactive bounding boxes
│   │   │   ├── InspectionHistory.tsx  # Audit log, search, status filtering, report downloads
│   │   │   ├── InspectionDetail.tsx   # Detailed deep dive on single inspection record
│   │   │   ├── RuleLibrary.tsx        # Rule 6 mapping library with legal citations
│   │   │   └── Settings.tsx           # Runtime diagnostics & engine configuration
│   │   ├── api.ts                     # API client functions with error handling
│   │   ├── types.ts                   # TypeScript domain models
│   │   ├── App.tsx                    # React router & responsive sidebar layout
│   │   └── index.css                  # Custom dark-mode design system & animations
│   ├── package.json
│   └── vite.config.ts
├── rules/
│   ├── rules.json             # Versioned Legal Metrology Rules (Rule 6 definitions)
│   └── rule_engine.py         # Deterministic validation engine (No LLM hallucinations)
├── demo/
│   ├── sample_images/         # Generated synthetic package labels for OCR testing
│   └── generate_sample_images.py
├── tests/
│   ├── test_rule_engine.py    # 26 Unit test cases verifying legal compliance rules
│   └── test_api_e2e.py        # End-to-end integration tests
├── docker/
│   └── Dockerfile             # Production container definition
├── requirements.txt
├── run.sh
└── README.md
```

---

## ✨ 5. Implemented Features

### 🔍 Vision & OCR Pipeline
- **Quality Assessment:** Evaluates Laplacian variance (blur), brightness, contrast, and resolution.
- **Preprocessing:** Bilateral/Non-local means denoising + CLAHE contrast enhancement.
- **OCR Engine:** EasyOCR with GPU/CPU support + graceful deterministic demo fallback.
- **Spatial Field Extraction:** Extracts and ranks candidates for:
  - Product Name (Spatial area & position heuristic)
  - Net Quantity (Metric units & values)
  - Maximum Retail Price / MRP (Currency symbols & numeric normalization)
  - Manufacturer / Packer / Importer details & addresses
  - Manufacturing / Packing date
  - Consumer Care helpline & email details
  - Country of Origin
- **Bounding Box Evidence:** Captures coordinate rectangles `[x1, y1, x2, y2]` and generates annotated visual overlays.

### ⚖️ Deterministic Legal Rule Engine
- **11 Versioned Legal Rules** directly mapped to Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011:
  - `LM-PC-001`: Product Name Declaration
  - `LM-PC-002`: Net Quantity Presence & Format
  - `LM-PC-003`: MRP Declaration (₹ / Rs. inclusive of taxes)
  - `LM-PC-004`: Manufacturer / Packer Name & Address
  - `LM-PC-005`: Consumer Care Details (Phone / Email)
  - `LM-PC-006`: Date of Mfg / Pkg / Import
  - `LM-PC-007`: Country of Origin (Imported goods)
  - `LM-PC-008`: Common / Generic Name
  - `LM-PC-009`: Net Quantity Numeric Value Check
  - `LM-PC-010`: MRP Numeric Value Check
  - `LM-PC-011`: Standard Metric Unit Validity
- **Confidence Protection:** OCR confidence `< 60%` triggers `NEEDS_REVIEW` instead of an unfair legal non-compliance penalty.
- **Explainability:** Every violation generates human-readable explanations detailing *Detected Value*, *Expected Requirement*, *Severity*, and *Rule Version*.

### 🖥️ Enforcement UI/UX
- **Flagship Inspection Screen:** Interactive 2-column view with image bounding box highlight, field declaration table, violation explanations, and review overrides.
- **Human-In-The-Loop:** Officer review modal with `Approve`, `Reject`, and `Edit Value` actions stored in the database audit log.
- **Executive Enforcement Dashboard:** Summary KPI metrics, violation trend analytics, recent inspections, and quick-demo launch buttons.
- **Audit History & Search:** Search by product name or Inspection ID with real-time status filtering (`Compliant`, `Non-Compliant`, `Needs Review`).
- **Official PDF Compliance Report:** Generates formatted multi-page enforcement reports with metadata, declaration tables, violation badges, and legal disclaimers.

---

## 🧪 6. Automated Verification (31 Tests Passing)
Run test suite:
```bash
python3 -m pytest tests/ -v
```
**Results: 31 passed in 1.5s (100% test pass rate)**
- `test_fully_compliant_product`
- `test_missing_mrp_declaration`
- `test_missing_manufacturer`
- `test_missing_consumer_care`
- `test_low_ocr_confidence_triggers_review`
- `test_non_standard_unit_declaration`
- `test_valid_metric_units` (Parameterized across units: g, kg, ml, L, pieces, nos)
- `test_valid_mrp_formats` (Parameterized across formats: ₹, Rs., MRP, etc.)
- `test_zero_numeric_value`
- `test_valid_date_formats` (Parameterized across date styles)
- `test_empty_ocr_result`
- `test_multiple_violations_calculation`
- `test_country_of_origin_detection`
- `test_evidence_bounding_box_retention`
- `test_versioned_rule_metadata`
- `test_api_health`
- `test_api_rules_list`
- `test_api_demo_products`
- `test_api_demo_scan_flow`
- `test_api_dashboard_stats`

---

## 🎬 7. Exact Demo Flow for Hackathon Judges

1. **Open Dashboard:** Navigate to [http://localhost:5173](http://localhost:5173). Show the executive summary cards, violation trends, and enforcement notice.
2. **Run Demo 1 (Fully Compliant):**
   - Click `"1. Fully Compliant Package"` on the dashboard or scanner.
   - Observe the step-by-step scanner progression.
   - Result: **COMPLIANT (100/100)**. Show the declaration mapping table.
3. **Run Demo 2 (Non-Compliant - Missing MRP):**
   - Click `"2. Missing MRP Declaration"`.
   - Result: **NON-COMPLIANT (82/100)**.
   - Highlight the red violation card: Rule `LM-PC-003`, explanation, and expected condition.
4. **Run Demo 4 (Human-in-the-Loop Review):**
   - Click `"3. Ambiguous / Low OCR Confidence"`.
   - Result: **NEEDS REVIEW**. Point out that low OCR confidence (`42%`) avoids unfair legal penalties.
   - Click `"Edit"` on the MRP row, enter corrected value `"₹199"`, and click `"Approve as Compliant"`.
   - Show how the audit trail logs the officer action.
5. **Real Image Upload Test:**
   - Upload any sample from `demo/sample_images/01_compliant_tea.jpg`.
   - Watch live EasyOCR execution with bounding box rendering.
6. **Download Report:**
   - Click `"Download PDF Report"` to open the official enforcement PDF with inspection ID and legal disclaimer.

---

## ⚠️ 8. Known Limitations & Production Roadmap
- **Packaging Distortion:** Severe curved cylindrical containers (cans, bottles) benefit from 3D unwarping in future revisions.
- **Multilingual OCR:** Current prototype handles English & Indian numerical formats; production will integrate IndicOCR (Hindi, Tamil, Marathi, Bengali).
- **Official Rule Calibration:** Prototype rules are mapped to the 2011 Rules and clearly tagged with a prototype disclaimer until officially gazetted by state authorities.
