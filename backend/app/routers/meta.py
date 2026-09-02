from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Inspection
from ..services.ocr import load_samples
from ..services.pipeline import serialize_inspection
from ..services.reports import ensure_report
from ..services.rule_engine import load_rule_pack

router = APIRouter()


@router.get("/rules")
def get_rules():
    pack = load_rule_pack()
    return pack


@router.get("/demo/samples")
def demo_samples():
    samples = load_samples()
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "scenario": s["scenario"],
            "demo": True,
            "image_url": f"/api/demo/samples/{s['id']}/image",
            "notes": s.get("notes") or "",
        }
        for s in samples
    ]


@router.get("/demo/samples/{sample_id}/image")
def demo_image(sample_id: str):
    from ..config import DEMO_DIR, ROOT

    samples = {s["id"]: s for s in load_samples()}
    s = samples.get(sample_id)
    if not s:
        raise HTTPException(404, "Sample not found")
    path = ROOT / s["image"]
    if not path.exists():
        path = DEMO_DIR / "images" / f"{sample_id}.png"
    if not path.exists():
        raise HTTPException(404, "Sample image missing — run python demo/generate_samples.py")
    return FileResponse(path, media_type="image/png")


@router.get("/files/inspections/{inspection_id}/image")
def inspection_image(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.get(Inspection, inspection_id)
    if not insp or not Path(insp.image_path).exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(insp.image_path, media_type="image/jpeg")


@router.get("/reports/{inspection_id}")
def report_json(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.get(Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, {"code": "not_found", "message": "Inspection not found."})
    rec = ensure_report(db, insp)
    data = serialize_inspection(insp)
    data["pdf_url"] = f"/api/reports/{inspection_id}/pdf"
    data["report_generated_at"] = rec.generated_at.isoformat() + "Z"
    return data


@router.get("/reports/{inspection_id}/pdf")
def report_pdf(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.get(Inspection, inspection_id)
    if not insp:
        raise HTTPException(404, {"code": "not_found", "message": "Inspection not found."})
    rec = ensure_report(db, insp)
    return FileResponse(rec.pdf_path, media_type="application/pdf", filename=f"{inspection_id}.pdf")


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    rows = db.query(Inspection).all()
    total = len(rows)
    counts = {"COMPLIANT": 0, "NON_COMPLIANT": 0, "NEEDS_REVIEW": 0}
    field_fails: dict[str, int] = {}
    for r in rows:
        counts[r.overall_status] = counts.get(r.overall_status, 0) + 1
        for v in r.violations:
            if v.status == "FAIL":
                field_fails[v.field_key] = field_fails.get(v.field_key, 0) + 1
    recent = sorted(rows, key=lambda x: x.created_at, reverse=True)[:8]
    common = sorted(field_fails.items(), key=lambda kv: -kv[1])[:6]
    # trend by day
    trend = {}
    for r in rows:
        day = r.created_at.strftime("%Y-%m-%d")
        trend.setdefault(day, {"COMPLIANT": 0, "NON_COMPLIANT": 0, "NEEDS_REVIEW": 0})
        trend[day][r.overall_status] = trend[day].get(r.overall_status, 0) + 1
    return {
        "total": total,
        "compliant": counts.get("COMPLIANT", 0),
        "non_compliant": counts.get("NON_COMPLIANT", 0),
        "needs_review": counts.get("NEEDS_REVIEW", 0),
        "common_violations": [{"field": k, "count": n} for k, n in common],
        "trend": [{"date": d, **v} for d, v in sorted(trend.items())],
        "recent": [
            {
                "id": r.id,
                "product_name": r.product_name,
                "overall_status": r.overall_status,
                "compliance_score": r.compliance_score,
                "created_at": r.created_at.isoformat() + "Z",
                "violation_count": r.violation_count,
            }
            for r in recent
        ],
    }
