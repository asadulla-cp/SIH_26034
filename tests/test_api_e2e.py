"""
MetaLex End-to-End API Integration Tests
Tests complete flow from Upload -> OCR/Demo -> Validation -> Database -> Report -> Review.
"""
import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "ocr_available" in data


def test_api_rules_list(client):
    res = client.get("/api/rules")
    assert res.status_code == 200
    data = res.json()
    assert len(data["rules"]) >= 10
    assert "disclaimer" in data


def test_api_demo_products(client):
    res = client.get("/api/demo/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 3


def test_api_demo_scan_flow(client):
    # Scan demo product
    res = client.post("/api/scan/demo/demo-001")
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "COMPLIANT"
    assert data["compliance_score"] == 100
    insp_id = data["id"]

    # Verify inspection is retrievable
    res_get = client.get(f"/api/inspections/{insp_id}")
    assert res_get.status_code == 200
    assert res_get.json()["product_name"] == "Tata Premium Tea"

    # Verify report generation works and returns PDF
    res_rep = client.get(f"/api/reports/{insp_id}")
    assert res_rep.status_code == 200
    assert res_rep.headers["content-type"] == "application/pdf"
    assert len(res_rep.content) > 1000

    # Submit officer review
    res_rev = client.post(f"/api/inspections/{insp_id}/review", json={
        "field_name": "mrp",
        "action": "APPROVE",
        "original_value": "₹199",
        "corrected_value": "₹199",
        "notes": "Verified by enforcement officer"
    })
    assert res_rev.status_code == 200


def test_api_dashboard_stats(client):
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_inspections" in stats
    assert stats["total_inspections"] >= 1
