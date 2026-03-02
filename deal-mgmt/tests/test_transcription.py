"""Transcription API 테스트 — 오디오 전사 + 미팅 로그 연동."""

import io
import uuid


# ── Upload validation ─────────────────────────────────────
async def test_upload_invalid_file_type(client, transaction_id):
    """허용되지 않는 파일 형식 업로드 → 400."""
    fake_file = io.BytesIO(b"not an audio file")
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/transcription",
        files={"audio": ("test.txt", fake_file, "text/plain")},
        data={
            "title": "테스트 회의",
            "meeting_date": "2026-03-01",
            "meeting_phase": "MARKETING",
        },
    )
    assert resp.status_code == 400


async def test_upload_missing_required_fields(client, transaction_id):
    """필수 필드 누락 → 422."""
    fake_file = io.BytesIO(b"\x00" * 100)
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/transcription",
        files={"audio": ("meeting.mp3", fake_file, "audio/mpeg")},
        # title 누락
        data={"meeting_date": "2026-03-01"},
    )
    assert resp.status_code == 422


async def test_upload_nonexistent_transaction(client):
    """존재하지 않는 거래 → 404."""
    fake_txn = str(uuid.uuid4())
    fake_file = io.BytesIO(b"\x00" * 100)
    resp = await client.post(
        f"/api/v1/transactions/{fake_txn}/transcription",
        files={"audio": ("meeting.mp3", fake_file, "audio/mpeg")},
        data={
            "title": "테스트 회의",
            "meeting_date": "2026-03-01",
            "meeting_phase": "MARKETING",
        },
    )
    assert resp.status_code == 404


# ── List ──────────────────────────────────────────────────
async def test_list_transcription_jobs_empty(client, transaction_id):
    """전사 작업 없는 상태 조회 → 빈 리스트."""
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/transcription")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Get nonexistent ───────────────────────────────────────
async def test_get_nonexistent_job(client, transaction_id):
    """존재하지 않는 작업 조회 → 404."""
    fake_job = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/transactions/{transaction_id}/transcription/{fake_job}")
    assert resp.status_code == 404


# ── Approve without completed job ─────────────────────────
async def test_approve_nonexistent_job(client, transaction_id):
    """존재하지 않는 작업 승인 → 404."""
    fake_job = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/transactions/{transaction_id}/transcription/{fake_job}/approve",
        json={
            "minutes": "회의록 내용",
            "summary": "요약",
        },
    )
    assert resp.status_code == 404


# ── Happy path: 유효한 오디오 업로드 ────────────────────
async def test_upload_valid_audio_accepted(client, transaction_id):
    """유효한 오디오 파일 업로드 → 202 Accepted (BackgroundTasks는 SQLite 환경에서 별도 검증)."""
    from unittest.mock import patch

    fake_audio = io.BytesIO(b"\xff\xfb\x90\x00" + b"\x00" * 1000)  # MP3 magic bytes
    with patch("app.routers.transcription.BackgroundTasks.add_task"):
        resp = await client.post(
            f"/api/v1/transactions/{transaction_id}/transcription",
            files={"audio": ("meeting.mp3", fake_audio, "audio/mpeg")},
            data={
                "title": "투자위원회 회의",
                "meeting_date": "2026-03-01",
                "meeting_phase": "MARKETING",
            },
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["title"] == "투자위원회 회의"
    assert "id" in data
    assert data["status"] in ("PENDING", "PROCESSING")
