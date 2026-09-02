from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, ensure_dirs, get_engine
from .models import RuleRecord
from .routers.api import router as api_router
from .routers.meta import router as meta_router
from .services.ocr import _try_live_ocr
from .services.rule_engine import load_rule_pack

app = FastAPI(title="MetaLex", version="1.0.0", description="Packaged commodity LM(PC) compliance prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    ensure_dirs()
    engine = get_engine()
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import Session

    from .models import Inspection
    from .services.ocr import load_samples
    from .services.pipeline import run_pipeline

    pack = load_rule_pack()
    with Session(engine) as db:
        for rule in pack["rules"]:
            db.merge(RuleRecord(
                rule_id=rule["rule_id"],
                field=rule["field"],
                description=rule["description"],
                requirement=rule["requirement"],
                severity=rule["severity"],
                validation_type=rule["validation_type"],
                version=rule["version"],
                legal_reference=rule.get("legal_reference", ""),
                demo_simplified=bool(rule.get("demo_simplified")),
            ))
        db.commit()
        if db.query(Inspection).count() == 0:
            for s in load_samples():
                try:
                    run_pipeline(db, sample_id=s["id"], officer_name="Seeded demo")
                except Exception:
                    pass


@app.get("/api/health")
def health():
    _, name = _try_live_ocr()
    return {
        "ok": True,
        "mode": "local",
        "ocr_engine": name,
        "database": "sqlite",
        "offline_capable": True,
        "rule_pack": load_rule_pack()["pack_id"],
        "rule_version": load_rule_pack()["version"],
    }


app.include_router(api_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
