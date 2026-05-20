import uuid

import pytest


def _agent_payload(name: str = "T") -> dict:
    return {
        "name": name,
        "description": None,
        "nodes": [
            {
                "id": "in",
                "type": "input",
                "label": "in",
                "position": {"x": 0, "y": 0},
                "config": {},
            },
            {
                "id": "out",
                "type": "output",
                "label": "out",
                "position": {"x": 200, "y": 0},
                "config": {},
            },
        ],
        "edges": [{"id": "e1", "source": "in", "target": "out"}],
        "entry_node_id": "in",
    }


@pytest.mark.asyncio
async def test_list_runs_empty(client):
    resp = await client.get("/api/v1/agent/runs")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_runs_with_filters(client):
    a = await client.post("/api/v1/agent/agents", json=_agent_payload("alpha"))
    assert a.status_code == 200
    agent_id = a.json()["id"]

    for _ in range(3):
        r = await client.post(
            f"/api/v1/agent/agents/{agent_id}/runs",
            json={"input": {}, "wait_for_completion": True},
        )
        assert r.status_code == 200

    listing = await client.get("/api/v1/agent/runs")
    assert listing.status_code == 200
    runs = listing.json()
    assert len(runs) == 3
    assert all(r["agent_id"] == agent_id for r in runs)
    assert all(r["status"] in {"completed", "failed"} for r in runs)

    filtered = await client.get(
        f"/api/v1/agent/runs?agent_id={agent_id}&status=completed&limit=2"
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) <= 2

    other_id = str(uuid.uuid4())
    none_resp = await client.get(f"/api/v1/agent/runs?agent_id={other_id}")
    assert none_resp.status_code == 200
    assert none_resp.json() == []
