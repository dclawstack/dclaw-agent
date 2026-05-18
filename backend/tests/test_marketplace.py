import pytest

AGENTS_BASE = "/api/v1/agent/agents"
MARKET_BASE = "/api/v1/agent/marketplace"

_AGENT_PAYLOAD = {
    "name": "Public Agent",
    "description": "A public agent",
    "nodes": [
        {"id": "n1", "type": "input", "label": "Input", "position": {"x": 0, "y": 0}, "config": {}},
    ],
    "edges": [],
    "entry_node_id": "n1",
}


async def _make_agent(client, name="Public Agent"):
    payload = {**_AGENT_PAYLOAD, "name": name}
    return (await client.post(AGENTS_BASE, json=payload)).json()


async def _publish(client, agent_id):
    return await client.post(f"{AGENTS_BASE}/{agent_id}/publish")


@pytest.mark.asyncio
async def test_marketplace_empty(client):
    r = await client.get(MARKET_BASE)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_marketplace_hides_private_agents(client):
    await _make_agent(client)
    r = await client.get(MARKET_BASE)
    assert r.json() == []


@pytest.mark.asyncio
async def test_marketplace_lists_published_agent(client):
    agent = await _make_agent(client)
    await _publish(client, agent["id"])
    r = await client.get(MARKET_BASE)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == agent["id"]


@pytest.mark.asyncio
async def test_marketplace_search_hit(client):
    agent = await _make_agent(client, name="Weather Bot")
    await _publish(client, agent["id"])
    r = await client.get(MARKET_BASE, params={"search": "Weather"})
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_marketplace_search_miss(client):
    agent = await _make_agent(client, name="Weather Bot")
    await _publish(client, agent["id"])
    r = await client.get(MARKET_BASE, params={"search": "Nonexistent"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_marketplace_install_public_agent(client):
    agent = await _make_agent(client)
    await _publish(client, agent["id"])
    r = await client.post(f"{MARKET_BASE}/{agent['id']}/install")
    assert r.status_code == 200
    assert r.json()["installed"] is True


@pytest.mark.asyncio
async def test_marketplace_install_private_agent_blocked(client):
    agent = await _make_agent(client)
    r = await client.post(f"{MARKET_BASE}/{agent['id']}/install")
    assert r.status_code == 404
