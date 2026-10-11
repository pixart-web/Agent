from fastapi.testclient import TestClient

from tests.test_execution_engine import register


def test_crm_manual_crud_and_duplicate_handling(client: TestClient) -> None:
    headers = register(client, "crm-api@example.com")
    organization_response = client.post(
        "/api/v1/crm/organizations",
        headers=headers,
        json={
            "name": "Northwind Portugal",
            "website": "https://northwind.example",
            "tags": ["customer", "retail"],
        },
    )
    assert organization_response.status_code == 201, organization_response.text
    organization = organization_response.json()
    updated = client.patch(
        f"/api/v1/crm/organizations/{organization['id']}",
        headers=headers,
        json={
            "organization_id": organization["id"],
            "status": "active",
            "tags": ["customer", "priority"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["tags"] == ["customer", "priority"]

    contact_response = client.post(
        "/api/v1/crm/contacts",
        headers=headers,
        json={
            "full_name": "Ana Silva",
            "organization_id": organization["id"],
            "job_title": "Commercial Director",
            "methods": [
                {
                    "method_type": "email",
                    "value": "ana@northwind.example",
                    "is_primary": True,
                }
            ],
            "tags": ["decision-maker"],
        },
    )
    assert contact_response.status_code == 201, contact_response.text
    contact = contact_response.json()
    assert contact["methods"][0]["value"] == "ana@northwind.example"

    client_response = client.post(
        "/api/v1/crm/clients",
        headers=headers,
        json={
            "organization_id": organization["id"],
            "lifecycle_status": "active",
            "industry": "Retail",
        },
    )
    assert client_response.status_code == 201, client_response.text
    crm_client = client_response.json()
    duplicate = client.post(
        "/api/v1/crm/clients",
        headers=headers,
        json={"organization_id": organization["id"]},
    )
    assert duplicate.status_code == 409

    pipeline_response = client.post(
        "/api/v1/crm/pipelines",
        headers=headers,
        json={
            "name": "Business sales",
            "is_default": True,
            "stages": [
                {"name": "Qualified", "position": 1, "default_probability": 40},
                {
                    "name": "Won",
                    "position": 2,
                    "default_probability": 100,
                    "is_terminal": True,
                },
            ],
        },
    )
    assert pipeline_response.status_code == 201, pipeline_response.text
    pipeline = pipeline_response.json()
    opportunity_response = client.post(
        "/api/v1/crm/opportunities",
        headers=headers,
        json={
            "client_id": crm_client["id"],
            "contact_id": contact["id"],
            "pipeline_id": pipeline["id"],
            "stage_id": pipeline["stages"][0]["id"],
            "title": "Portugal rollout",
            "amount_minor": 1250000,
            "currency": "EUR",
            "expected_close_on": "2026-12-15",
        },
    )
    assert opportunity_response.status_code == 201, opportunity_response.text
    opportunity = opportunity_response.json()
    moved = client.patch(
        f"/api/v1/crm/opportunities/{opportunity['id']}",
        headers=headers,
        json={
            "opportunity_id": opportunity["id"],
            "stage_id": pipeline["stages"][1]["id"],
            "status": "won",
            "probability": 100,
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "won"


def test_crm_import_preview_confirm_and_safe_export(client: TestClient) -> None:
    headers = register(client, "crm-import@example.com")
    content = (
        b"record_type,name,website,organization_name,email,phone,tags\n"
        b"organization,=Formula Ltd,https://formula.example,,,,customer\n"
        b"contact,Joana Costa,,=Formula Ltd,joana@formula.example,,decision-maker\n"
    )
    preview = client.post(
        "/api/v1/crm/import/preview",
        headers=headers,
        files={"upload": ("crm.csv", content, "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid_rows"] == 2
    assert preview.json()["invalid_rows"] == 0

    changed = client.post(
        "/api/v1/crm/import/confirm",
        headers=headers,
        data={"fingerprint": preview.json()["fingerprint"]},
        files={"upload": ("crm.csv", content + b"\n", "text/csv")},
    )
    assert changed.status_code == 409

    confirmed = client.post(
        "/api/v1/crm/import/confirm",
        headers=headers,
        data={"fingerprint": preview.json()["fingerprint"]},
        files={"upload": ("crm.csv", content, "text/csv")},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["created"] == 2

    exported = client.get("/api/v1/crm/export?resource=organizations&format=csv", headers=headers)
    assert exported.status_code == 200
    assert "'=Formula Ltd" in exported.text
    assert "attachment" in exported.headers["content-disposition"]

    invalid = client.post(
        "/api/v1/crm/import/preview",
        headers=headers,
        files={
            "upload": (
                "invalid.csv",
                b"record_type,name,email\ncontact,Broken,not-an-email\n",
                "text/csv",
            )
        },
    )
    assert invalid.status_code == 200
    assert invalid.json()["invalid_rows"] == 1
