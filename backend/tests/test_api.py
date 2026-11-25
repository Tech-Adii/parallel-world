"""Integration tests for FastAPI REST endpoints and City Builder / SQLite persistence."""

from fastapi.testclient import TestClient

from app.main import app


def test_rest_api_workflow():
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        state_resp = client.get("/api/state")
        assert state_resp.status_code == 200
        data = state_resp.json()
        assert "primary" in data
        assert "parallel" in data
        assert len(data["cities"]) >= 3

        # Toggle emergency response & alternative routes
        act = client.post(
            "/api/simulation/intervention",
            json={"universe_id": "primary", "action": "deploy_emergency_response"},
        )
        assert act.status_code == 200
        assert act.json()["primary"]["interventions"]["emergency_response_active"] is True

        # Place a new hospital on an empty tile
        edit = client.post(
            "/api/simulation/tile",
            json={"x": 1, "y": 0, "tile_type": "hospital"},
        )
        assert edit.status_code == 200

        # Step simulation & inspect Time Machine stack
        step_resp = client.post("/api/simulation/step")
        assert step_resp.status_code == 200
        tick_after = step_resp.json()["primary"]["tick"]

        tm_resp = client.get("/api/timemachine/primary")
        assert tm_resp.status_code == 200
        assert tm_resp.json()["current_tick"] == tick_after
        assert tm_resp.json()["can_undo"] is True

        # Ask AI City Administrator
        ai_resp = client.post("/api/ai/advice", json={"universe_id": "primary", "question": "What should we prioritize?"})
        assert ai_resp.status_code == 200
        assert len(ai_resp.json()["recommendations"]) >= 1
