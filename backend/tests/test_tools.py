import pytest

TOOLS_BASE = "/api/v1/agent/tools"


@pytest.mark.asyncio
async def test_list_tools_returns_all_builtins(client):
    r = await client.get(TOOLS_BASE)
    assert r.status_code == 200
    tools = r.json()
    assert len(tools) == 5
    slugs = {t["slug"] for t in tools}
    assert slugs == {"web_search", "calculator", "api_caller", "file_reader", "code_executor"}


@pytest.mark.asyncio
async def test_get_tool_by_slug(client):
    r = await client.get(f"{TOOLS_BASE}/calculator")
    assert r.status_code == 200
    t = r.json()
    assert t["slug"] == "calculator"
    assert t["is_builtin"] is True
    assert t["is_installed"] is False


@pytest.mark.asyncio
async def test_get_tool_not_found(client):
    r = await client.get(f"{TOOLS_BASE}/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_install_tool(client):
    r = await client.post(f"{TOOLS_BASE}/calculator/install")
    assert r.status_code == 200
    assert r.json()["is_installed"] is True


@pytest.mark.asyncio
async def test_uninstall_tool(client):
    await client.post(f"{TOOLS_BASE}/calculator/install")
    r = await client.delete(f"{TOOLS_BASE}/calculator/install")
    assert r.status_code == 204
    r = await client.get(f"{TOOLS_BASE}/calculator")
    assert r.json()["is_installed"] is False


@pytest.mark.asyncio
async def test_install_nonexistent_tool(client):
    r = await client.post(f"{TOOLS_BASE}/nonexistent/install")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_execute_calculator(client):
    r = await client.post(
        f"{TOOLS_BASE}/calculator/execute",
        json={"inputs": {"expression": "2 ** 10 + 5"}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == 1029


@pytest.mark.asyncio
async def test_execute_calculator_invalid_expression(client):
    r = await client.post(
        f"{TOOLS_BASE}/calculator/execute",
        json={"inputs": {"expression": "__import__('os').system('id')"}},
    )
    assert r.status_code == 200
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_execute_file_reader_missing_file(client):
    r = await client.post(
        f"{TOOLS_BASE}/file_reader/execute",
        json={"inputs": {"path": "does_not_exist.txt"}},
    )
    assert r.status_code == 200
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_execute_code_executor(client):
    r = await client.post(
        f"{TOOLS_BASE}/code_executor/execute",
        json={"inputs": {"code": "print('hello world')", "timeout": 5}},
    )
    assert r.status_code == 200
    data = r.json()
    assert "hello world" in data["stdout"]
    assert data["exit_code"] == 0


@pytest.mark.asyncio
async def test_execute_nonexistent_tool(client):
    r = await client.post(
        f"{TOOLS_BASE}/nonexistent/execute",
        json={"inputs": {}},
    )
    assert r.status_code == 404
