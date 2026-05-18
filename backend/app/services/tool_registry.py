import ast
import operator
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

BUILTIN_TOOLS = [
    {
        "slug": "web_search",
        "name": "Web Search",
        "description": "Search the web using DuckDuckGo and return top results.",
        "category": "search",
        "config_schema": {"query": "string — search query"},
    },
    {
        "slug": "calculator",
        "name": "Calculator",
        "description": "Safely evaluate mathematical expressions (+, -, *, /, **, %).",
        "category": "compute",
        "config_schema": {"expression": "string — math expression e.g. '2 ** 10 + 5'"},
    },
    {
        "slug": "api_caller",
        "name": "API Caller",
        "description": "Make HTTP requests to any REST API endpoint.",
        "category": "integration",
        "config_schema": {
            "url": "string",
            "method": "GET|POST|PUT|DELETE",
            "headers": "object (optional)",
            "body": "object (optional)",
        },
    },
    {
        "slug": "file_reader",
        "name": "File Reader",
        "description": "Read text files from the workspace (/tmp/dclaw_workspace).",
        "category": "io",
        "config_schema": {"path": "string — relative path inside workspace"},
    },
    {
        "slug": "code_executor",
        "name": "Code Executor",
        "description": "Execute Python code in an isolated subprocess (max 5s).",
        "category": "code",
        "config_schema": {
            "code": "string — Python source code",
            "timeout": "int — seconds, default 5, max 30",
        },
    },
]

_WORKSPACE = Path("/tmp/dclaw_workspace")

# Safe AST-based calculator
_BINOP_MAP: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNOP_MAP: dict[type, Any] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        return node.value
    if isinstance(node, ast.BinOp):
        op_fn = _BINOP_MAP.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op)}")
        return op_fn(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_fn = _UNOP_MAP.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        return op_fn(_safe_eval(node.operand))
    raise ValueError(f"Unsupported AST node: {type(node)}")


async def _execute_web_search(inputs: dict[str, Any]) -> dict[str, Any]:
    query = inputs.get("query", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_redirect": "1"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("Results", []):
                results.append(
                    {
                        "title": item.get("Text", ""),
                        "snippet": item.get("Text", ""),
                        "url": item.get("FirstURL", ""),
                    }
                )
            # Also include RelatedTopics
            for item in data.get("RelatedTopics", []):
                if isinstance(item, dict) and "Text" in item:
                    results.append(
                        {
                            "title": item.get("Text", ""),
                            "snippet": item.get("Text", ""),
                            "url": item.get("FirstURL", ""),
                        }
                    )
            return {"query": query, "results": results[:10]}
    except Exception as exc:
        return {"error": str(exc), "results": []}


def _execute_calculator(inputs: dict[str, Any]) -> dict[str, Any]:
    expression = inputs.get("expression", "")
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return {"expression": expression, "result": result}
    except Exception as exc:
        return {"expression": expression, "error": str(exc)}


async def _execute_api_caller(inputs: dict[str, Any]) -> dict[str, Any]:
    url = inputs.get("url", "")
    method = inputs.get("method", "GET").upper()
    headers = inputs.get("headers") or {}
    body = inputs.get("body")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, json=body, headers=headers)
            elif method == "PUT":
                resp = await client.put(url, json=body, headers=headers)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                return {"error": f"Unsupported method: {method}"}
            try:
                response_body = resp.json()
            except Exception:
                response_body = resp.text
            return {"status_code": resp.status_code, "body": response_body}
    except Exception as exc:
        return {"error": str(exc)}


def _execute_file_reader(inputs: dict[str, Any]) -> dict[str, Any]:
    raw_path = inputs.get("path", "")
    try:
        _WORKSPACE.mkdir(parents=True, exist_ok=True)
        # Resolve and sandbox
        target = (_WORKSPACE / raw_path).resolve()
        workspace_resolved = _WORKSPACE.resolve()
        if not str(target).startswith(str(workspace_resolved)):
            return {"error": "Path traversal detected — access denied"}
        if not target.exists():
            return {"error": f"File not found: {raw_path}"}
        if not target.is_file():
            return {"error": f"Not a file: {raw_path}"}
        max_bytes = 50 * 1024  # 50KB
        content = target.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
        return {"path": raw_path, "content": content, "size": target.stat().st_size}
    except Exception as exc:
        return {"error": str(exc)}


def _execute_code_executor(inputs: dict[str, Any]) -> dict[str, Any]:
    code = inputs.get("code", "")
    timeout = min(int(inputs.get("timeout", 5) or 5), 30)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "Execution timed out", "exit_code": -1}
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as exc:
        return {"error": str(exc)}


async def execute_builtin_tool(slug: str, inputs: dict[str, Any]) -> dict[str, Any]:
    if slug == "web_search":
        return await _execute_web_search(inputs)
    if slug == "calculator":
        return _execute_calculator(inputs)
    if slug == "api_caller":
        return await _execute_api_caller(inputs)
    if slug == "file_reader":
        return _execute_file_reader(inputs)
    if slug == "code_executor":
        return _execute_code_executor(inputs)
    return {"error": f"Unknown tool slug: {slug}"}
