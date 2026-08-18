from fastapi.testclient import TestClient


def signup(client: TestClient, email: str = "astro@example.com") -> None:
    response = client.post("/api/auth/signup", json={"name": "Astro User", "email": email, "password": "strong-password"})
    assert response.status_code == 201
    client.headers["Authorization"] = f"Bearer {response.json()['data']['access_token']}"


def birth(name: str) -> dict:
    return {"name": name, "date_of_birth": "1994-07-12", "time_of_birth": "08:30", "place": "Kanpur, India"}


def test_kundli_is_cached_and_pdf_is_downloadable(client: TestClient) -> None:
    signup(client)
    first = client.post("/api/kundli", json={"birth_details": birth("Astro User")})
    assert first.status_code == 200
    chart = first.json()["data"]
    assert len(chart["planets"]) == 9
    assert chart["calculation"]["provider"] == "mock"

    latest = client.get("/api/kundli/latest")
    assert latest.status_code == 200
    assert latest.json()["data"]["id"] == chart["id"]

    pdf = client.get(f"/api/reports/{chart['report_id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    another = client.post("/api/kundli", json={"birth_details": birth("Another Person")})
    assert another.status_code == 200
    assert another.json()["data"]["id"] != chart["id"]
    assert client.get("/api/reports").status_code == 200
    assert len(client.get("/api/reports").json()["data"]) == 2


def test_compatibility_and_report_ownership(client: TestClient) -> None:
    match = client.post("/api/compatibility", json={"person_a": birth("Person A"), "person_b": birth("Person B")})
    assert match.status_code == 200
    data = match.json()["data"]
    assert 0 <= data["overall_score"] <= 100
    assert {item["name"] for item in data["components"]} == {"Emotional", "Communication", "Lifestyle", "Long-term"}

    reports = client.get("/api/reports")
    assert reports.status_code == 200
    assert len(reports.json()["data"]) == 3
    protected_id = data["report_id"]

    client.post("/api/auth/logout")
    client.headers.pop("Authorization", None)
    signup(client, "second@example.com")
    assert client.get(f"/api/reports/{protected_id}").status_code == 404
