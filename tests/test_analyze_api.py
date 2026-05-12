from __future__ import annotations


def _start_session(client, mode: str, goal: str | None = None) -> str:
    payload = {"user_id": "default", "mode": mode}
    if goal is not None:
        payload["goal"] = goal
    response = client.post("/api/sessions/start", json=payload)
    assert response.status_code == 200
    return response.json()["session_id"]


def _file(image_bytes: bytes):
    return {"file": ("frame.jpg", image_bytes, "image/jpeg")}


def test_exercise_analyze_fallback_returns_update_without_500(client, image_bytes):
    session_id = _start_session(client, "exercise", "squat")

    response = client.post(
        "/api/analyze/exercise",
        data={"session_id": session_id},
        files=_file(image_bytes),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["type"] == "exercise_update"
    assert "count" in body["exercise"]
    assert "coaching" not in body
    assert _has_no_mojibake(body["feedback"])


def test_exercise_frame_update_has_no_coaching_but_stop_does(client, image_bytes):
    session_id = _start_session(client, "exercise", "squat")

    frame_update = client.post(
        "/api/analyze/exercise",
        data={"session_id": session_id},
        files=_file(image_bytes),
    )
    assert frame_update.status_code == 200
    assert "coaching" not in frame_update.json()

    stop = client.post(f"/api/sessions/{session_id}/stop")
    assert stop.status_code == 200
    body = stop.json()
    assert body["coaching"] is not None
    assert body["features"]["exercise"] is not None


def test_exercise_websocket_gate_broadcasts_update_and_stop_returns_coaching(client, image_bytes):
    session_response = client.post(
        "/api/sessions/start",
        json={"user_id": "default", "mode": "exercise", "goal": "squat"},
    )
    assert session_response.status_code == 200
    session_body = session_response.json()
    session_id = session_body["session_id"]
    assert session_body["ws_url"].endswith(f"/ws/sessions/{session_id}")

    with client.websocket_connect(f"/ws/sessions/{session_id}") as websocket:
        frame_update = client.post(
            "/api/analyze/exercise",
            data={"session_id": session_id},
            files=_file(image_bytes),
        )
        assert frame_update.status_code == 200
        frame_body = frame_update.json()
        assert "coaching" not in frame_body

        message = websocket.receive_json()
        assert message["type"] == "exercise_update"
        assert message["session_id"] == session_id
        assert message["count"] == frame_body["exercise"]["count"]
        assert message["state"] == frame_body["exercise"]["state"]
        assert message["posture_errors"] == frame_body["exercise"]["posture_errors"]
        assert message["stability_score"] == frame_body["exercise"]["stability_score"]
        assert _has_no_mojibake(message["feedback"])

    stop = client.post(f"/api/sessions/{session_id}/stop")
    assert stop.status_code == 200
    stop_body = stop.json()
    assert stop_body["coaching"] is not None
    assert stop_body["features"]["exercise"] is not None


def test_exercise_session_goal_sets_final_exercise_type(client):
    session_response = client.post(
        "/api/sessions/start",
        json={"user_id": "default", "mode": "exercise", "goal": "pushup"},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    stop = client.post(f"/api/sessions/{session_id}/stop")

    assert stop.status_code == 200
    body = stop.json()
    assert body["features"]["exercise"]["type"] == "pushup"
    assert body["coaching"]["exercise_plan"][0]["exercise"] == "pushup"


def test_removed_non_exercise_modes_are_not_available(client, image_bytes):
    start_response = client.post(
        "/api/sessions/start",
        json={"user_id": "default", "mode": "grooming"},
    )
    assert start_response.status_code == 422

    analyze_response = client.post(
        "/api/analyze/grooming",
        data={"session_id": "sess_missing"},
        files=_file(image_bytes),
    )
    assert analyze_response.status_code == 404


def _has_no_mojibake(text: str) -> bool:
    return not any(marker in text for marker in ["�", "占", "醫", "臾", "?꾩", "덈떎"])
