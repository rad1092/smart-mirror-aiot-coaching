from __future__ import annotations


def test_get_unknown_user_baseline_returns_default(client):
    response = client.get("/api/baselines/users/unknown_user")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "unknown_user"
    assert body["source"] == "default"
    assert "exercise" in body["baseline"]
    assert "face" in body["baseline"]


def test_upsert_and_get_user_baseline(client):
    payload = {
        "exercise": {
            "squat": {
                "avg_count": 7,
                "avg_stability_score": 0.67,
            }
        },
        "face": {
            "brightness": 0.55,
            "redness": 0.2,
            "beard_shadow": 0.35,
        },
        "outfit": {
            "preferred_tones": ["navy"],
            "preferred_colors": ["navy", "white"],
        },
    }

    save_response = client.post("/api/baselines/users/api_user_1", json=payload)
    get_response = client.get("/api/baselines/users/api_user_1")

    assert save_response.status_code == 200
    assert get_response.status_code == 200
    saved = save_response.json()
    loaded = get_response.json()
    assert saved["status"] == "saved"
    assert saved["source"] == "user"
    assert loaded["source"] == "user"
    assert loaded["baseline"]["exercise"]["squat"]["avg_count"] == 7
    assert loaded["baseline"]["face"]["brightness"] == 0.55
    assert loaded["baseline"]["outfit"]["preferred_colors"] == ["navy", "white"]
