import pytest


@pytest.mark.asyncio
async def test_auth_flow_and_presign(client):
    register_resp = await client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "Password123"},
    )
    assert register_resp.status_code == 201

    login_resp = await client.post(
        "/auth/login",
        data={"username": "user@example.com", "password": "Password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "user@example.com"

    presign_resp = await client.post(
        "/files/presign",
        json={"filename": "sample.mp3", "content_type": "audio/mpeg"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presign_resp.status_code == 200
    presign_data = presign_resp.json()
    assert presign_data["object_key"].endswith("sample.mp3")
    assert presign_data["upload_url"].startswith("https://example.com/put/")

    job_resp = await client.post(
        "/jobs/",
        json={
            "object_key": presign_data["object_key"],
            "language": "en",
            "mode": "mono",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_resp.status_code == 201
    job_data = job_resp.json()
    assert job_data["status"] == "pending"

    jobs_list = await client.get(
        "/jobs/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert jobs_list.status_code == 200
    items = jobs_list.json()
    assert len(items) == 1
    assert items[0]["id"] == job_data["id"]
