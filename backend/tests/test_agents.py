import pytest

BASE = "/api/v1/agent/agents"

AGENT_PAYLOAD = {
    "name": "Test Agent",
    "description": "A test agent",
    "nodes": [
        {"id": "n1", "type": "input", "label": "Input", "position": {"x": 0, "y": 0}, "config": {}},
        {"id": "n2", "type": "output", "label": "Output", "position": {"x": 200, "y": 0}, "config": {}},
    ],
    "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    "entry_node_id": "n1",
}


@pytest.mark.asyncio
async def test_create_agent(client):
    r = await client.post(BASE, json=AGENT_PAYLOAD)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Agent"
    assert data["version"] == 1
    assert data["is_public"] is False


@pytest.mark.asyncio
async def test_list_agents_empty(client):
    r = await client.get(BASE)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_agents(client):
    await client.post(BASE, json=AGENT_PAYLOAD)
    r = await client.get(BASE)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_agent(client):
    created = (await client.post(BASE, json=AGENT_PAYLOAD)).json()
    r = await client.get(f"{BASE}/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_agent_not_found(client):
    r = await client.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_agent_name(client):
    created = (await client.post(BASE, json=AGENT_PAYLOAD)).json()
    r = await client.patch(f"{BASE}/{created['id']}", json={"name": "Updated"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Updated"
    assert data["version"] == 2


@pytest.mark.asyncio
async def test_update_agent_not_found(client):
    r = await client.patch(
        f"{BASE}/00000000-0000-0000-0000-000000000000", json={"name": "X"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_agent(client):
    created = (await client.post(BASE, json=AGENT_PAYLOAD)).json()
    r = await client.delete(f"{BASE}/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"{BASE}/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_agent_not_found(client):
    r = await client.delete(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_publish_agent(client):
    created = (await client.post(BASE, json=AGENT_PAYLOAD)).json()
    r = await client.post(f"{BASE}/{created['id']}/publish")
    assert r.status_code == 200
    assert r.json()["is_public"] is True


@pytest.mark.asyncio
async def test_publish_agent_not_found(client):
    r = await client.post(f"{BASE}/00000000-0000-0000-0000-000000000000/publish")
    assert r.status_code == 404
