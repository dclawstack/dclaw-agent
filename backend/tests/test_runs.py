import pytest

AGENTS_BASE = "/api/v1/agent/agents"
RUNS_BASE = "/api/v1/agent/runs"

_SIMPLE_AGENT = {
    "name": "Simple Agent",
    "nodes": [
        {"id": "n1", "type": "input", "label": "Input", "position": {"x": 0, "y": 0}, "config": {}},
        {"id": "n2", "type": "output", "label": "Output", "position": {"x": 200, "y": 0}, "config": {}},
    ],
    "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    "entry_node_id": "n1",
}


async def _make_agent(client, payload=None):
    return (await client.post(AGENTS_BASE, json=payload or _SIMPLE_AGENT)).json()


# --- create run ---

@pytest.mark.asyncio
async def test_create_run_returns_pending(client):
    agent = await _make_agent(client)
    r = await client.post(f"{RUNS_BASE}/{agent['id']}/runs", json={"input": {}})
    assert r.status_code == 200
    assert r.json()["agent_id"] == agent["id"]
    assert r.json()["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_create_run_agent_not_found(client):
    r = await client.post(
        f"{RUNS_BASE}/00000000-0000-0000-0000-000000000000/runs", json={"input": {}}
    )
    assert r.status_code == 404


# --- get run ---

@pytest.mark.asyncio
async def test_get_run(client):
    agent = await _make_agent(client)
    run = (await client.post(f"{RUNS_BASE}/{agent['id']}/runs", json={"input": {}})).json()
    r = await client.get(f"{RUNS_BASE}/{run['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == run["id"]


@pytest.mark.asyncio
async def test_get_run_not_found(client):
    r = await client.get(f"{RUNS_BASE}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# --- cancel run ---

@pytest.mark.asyncio
async def test_cancel_run(client):
    agent = await _make_agent(client)
    run = (await client.post(f"{RUNS_BASE}/{agent['id']}/runs", json={"input": {}})).json()
    r = await client.post(f"{RUNS_BASE}/{run['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] in ("pending", "cancelled")


@pytest.mark.asyncio
async def test_cancel_run_not_found(client):
    r = await client.post(f"{RUNS_BASE}/00000000-0000-0000-0000-000000000000/cancel")
    assert r.status_code == 404


# --- execution engine (wait_for_completion=True) ---

@pytest.mark.asyncio
async def test_run_completes_input_output_graph(client):
    agent = await _make_agent(client)
    r = await client.post(
        f"{RUNS_BASE}/{agent['id']}/runs",
        json={"input": {"text": "hello"}, "wait_for_completion": True},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    assert run["step_count"] == 2


@pytest.mark.asyncio
async def test_run_records_step_count(client):
    agent = await _make_agent(client)
    r = await client.post(
        f"{RUNS_BASE}/{agent['id']}/runs",
        json={"input": {}, "wait_for_completion": True},
    )
    assert r.json()["step_count"] >= 1


@pytest.mark.asyncio
async def test_run_llm_node_echo_fallback(client):
    # Ollama is not running in CI — execution falls back to "[echo] …" and still completes
    payload = {
        "name": "LLM Agent",
        "nodes": [
            {"id": "n1", "type": "input", "label": "Input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "n2", "type": "llm", "label": "LLM", "position": {"x": 100, "y": 0}, "config": {"prompt": "say hello"}},
            {"id": "n3", "type": "output", "label": "Output", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
        ],
        "entry_node_id": "n1",
    }
    agent = await _make_agent(client, payload)
    r = await client.post(
        f"{RUNS_BASE}/{agent['id']}/runs",
        json={"input": {}, "wait_for_completion": True},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    assert run["step_count"] == 3


@pytest.mark.asyncio
async def test_run_condition_takes_true_branch(client):
    payload = {
        "name": "Condition Agent",
        "nodes": [
            {"id": "n1", "type": "input", "label": "Input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "n2", "type": "condition", "label": "Check", "position": {"x": 100, "y": 0}, "config": {"expression": "True"}},
            {"id": "n3", "type": "output", "label": "Yes", "position": {"x": 200, "y": -50}, "config": {}},
            {"id": "n4", "type": "output", "label": "No", "position": {"x": 200, "y": 50}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3", "condition": "true"},
            {"id": "e3", "source": "n2", "target": "n4", "condition": "false"},
        ],
        "entry_node_id": "n1",
    }
    agent = await _make_agent(client, payload)
    r = await client.post(
        f"{RUNS_BASE}/{agent['id']}/runs",
        json={"input": {}, "wait_for_completion": True},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    assert run["step_count"] == 3  # input + condition + yes-branch output


@pytest.mark.asyncio
async def test_run_respects_max_steps(client):
    # Self-looping graph: execution must stop at max_steps, not run forever
    payload = {
        "name": "Loop Agent",
        "nodes": [
            {"id": "n1", "type": "input", "label": "Start", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "n2", "type": "input", "label": "Loop", "position": {"x": 100, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n2"},
        ],
        "entry_node_id": "n1",
        "max_steps": 3,
    }
    agent = await _make_agent(client, payload)
    r = await client.post(
        f"{RUNS_BASE}/{agent['id']}/runs",
        json={"input": {}, "wait_for_completion": True},
    )
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "completed"
    assert run["step_count"] <= 3
