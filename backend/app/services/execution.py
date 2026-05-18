import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent import AgentDefinition, AgentRun, StepLog


async def call_ollama(prompt: str, system: str | None = None) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload: dict[str, Any] = {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system
            resp = await client.post(
                f"{settings.ollama_url}/api/generate", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except Exception:
        return f"[echo] {prompt}"


async def execute_node(
    session: AsyncSession,
    run: AgentRun,
    node: dict[str, Any],
    node_outputs: dict[str, Any],
    step_number: int,
) -> dict[str, Any]:
    node_type = node.get("type", "")
    config = node.get("config", {})
    inputs = resolve_inputs(node, node_outputs)

    step = StepLog(
        run_id=run.id,
        step_number=step_number,
        node_id=node["id"],
        node_type=node_type,
        status="running",
        input=inputs,
    )
    session.add(step)
    await session.commit()

    try:
        output: dict[str, Any]
        if node_type == "input":
            output = inputs
        elif node_type == "llm":
            prompt = config.get("prompt", inputs.get("text", ""))
            system = config.get("system_prompt", "")
            response = await call_ollama(prompt, system)
            output = {"text": response}
        elif node_type == "tool":
            tool_slug = config.get("tool_slug")
            if tool_slug:
                from app.services.tool_registry import execute_builtin_tool
                output = await execute_builtin_tool(tool_slug, inputs)
            else:
                output = await call_tool(config, inputs)
        elif node_type == "memory":
            from app.services.memory import store_memory, retrieve_memories
            action = config.get("action", "store")
            scope = config.get("scope", "global")
            if action == "retrieve":
                query = inputs.get("query", config.get("query", ""))
                top_k = int(config.get("top_k", 5))
                memories = await retrieve_memories(session, scope, query, top_k)
                output = {"memories": [{"key": m.key, "content": m.content, "importance": m.importance} for m in memories]}
            else:  # store
                key = inputs.get("key", config.get("key", f"memory_{step_number}"))
                content = str(inputs.get("content", inputs.get("text", str(inputs))))
                importance = float(config.get("importance", 0.5))
                mem = await store_memory(session, scope, "episodic", key, content, importance)
                output = {"stored": True, "memory_id": str(mem.id), "key": mem.key}
        elif node_type == "condition":
            expr = config.get("expression", "true")
            output = {"result": eval_condition(expr, inputs)}
        elif node_type == "output":
            output = inputs
        else:
            output = inputs

        step.status = "completed"
        step.output = output
        step.completed_at = datetime.now(timezone.utc)
        await session.commit()
        return output
    except Exception as exc:
        step.status = "failed"
        step.error = str(exc)
        step.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise


async def call_tool(config: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    url = config.get("url", "")
    method = config.get("method", "GET")
    headers = config.get("headers", {})
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method.upper() == "POST":
            resp = await client.post(url, json=inputs, headers=headers)
        else:
            resp = await client.get(url, params=inputs, headers=headers)
        return {"status_code": resp.status_code, "body": resp.text}


def eval_condition(expr: str, inputs: dict[str, Any]) -> bool:
    try:
        return bool(eval(expr, {"__builtins__": {}}, inputs))
    except Exception:
        return False


def resolve_inputs(node: dict[str, Any], node_outputs: dict[str, Any]) -> dict[str, Any]:
    config = node.get("config", {})
    resolved: dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            ref = value[2:-2].strip()
            parts = ref.split(".")
            if len(parts) >= 2:
                src_id = parts[0]
                src_key = parts[1]
                resolved[key] = node_outputs.get(src_id, {}).get(src_key, value)
            else:
                resolved[key] = node_outputs.get(ref, value)
        else:
            resolved[key] = value
    return resolved


async def execute_agent(
    session: AsyncSession,
    run: AgentRun,
    agent: AgentDefinition,
) -> None:
    run.status = "running"
    await session.commit()

    start = time.time()
    nodes = {n["id"]: n for n in agent.nodes}
    adjacency: dict[str, list[str]] = {}
    for edge in agent.edges:
        adjacency.setdefault(edge["source"], []).append(edge["target"])

    current = agent.entry_node_id
    node_outputs: dict[str, Any] = {}
    step_number = 0

    try:
        while current and step_number < agent.max_steps:
            node = nodes.get(current)
            if not node:
                break
            step_number += 1
            output = await execute_node(
                session, run, node, node_outputs, step_number
            )
            node_outputs[current] = output
            run.step_count = step_number
            await session.commit()

            if node.get("type") == "output":
                break

            next_nodes = adjacency.get(current, [])
            if not next_nodes:
                break

            if node.get("type") == "condition" and next_nodes:
                condition_result = output.get("result", True)
                chosen = None
                for edge in agent.edges:
                    if edge["source"] == current:
                        expr = edge.get("condition", "")
                        if not expr or (expr == "true" and condition_result) or (expr == "false" and not condition_result):
                            chosen = edge["target"]
                            break
                current = chosen
            else:
                current = next_nodes[0] if next_nodes else None

        run.status = "completed"
        run.output = node_outputs
    except Exception:
        run.status = "failed"
    finally:
        run.completed_at = datetime.now(timezone.utc)
        run.duration_ms = int((time.time() - start) * 1000)
        await session.commit()
