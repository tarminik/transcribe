import pytest

from app.db.session import get_session_factory
from app.models import (
    Transcript,
    TranscriptionHistory,
    TranscriptionJob,
    TranscriptionStatus,
)


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


@pytest.mark.asyncio
async def test_history_listing_and_detail(client):
    register_resp = await client.post(
        "/auth/register",
        json={"email": "history@example.com", "password": "Password123"},
    )
    assert register_resp.status_code == 201

    login_resp = await client.post(
        "/auth/login",
        data={"username": "history@example.com", "password": "Password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    user_id = me_resp.json()["id"]

    presign_resp = await client.post(
        "/files/presign",
        json={"filename": "history.mp3", "content_type": "audio/mpeg"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presign_resp.status_code == 200
    object_key = presign_resp.json()["object_key"]

    job_resp = await client.post(
        "/jobs/",
        json={
            "object_key": object_key,
            "language": "en",
            "mode": "mono",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        job = await session.get(TranscriptionJob, job_id)
        assert job is not None
        job.status = TranscriptionStatus.COMPLETED
        job.result_object_key = "results/test.txt"
        job.error_message = None

        transcript = Transcript(job_id=job_id, plain_text="Hello history!", diarized_json=None)
        history_entry = TranscriptionHistory(
            user_id=user_id,
            job_id=job_id,
            title="history.mp3",
        )
        session.add_all([transcript, history_entry])
        await session.commit()

    history_resp = await client.get(
        "/history/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_resp.status_code == 200
    items = history_resp.json()
    assert len(items) == 1
    history_id = items[0]["id"]
    assert items[0]["title"] == "history.mp3"

    detail_resp = await client.get(
        f"/history/{history_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["transcript_text"] == "Hello history!"
    assert detail["job_id"] == job_id
