import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition, AgentRun
from app.models.team import AgentTeam, TeamRun
from app.services.execution import execute_agent


async def execute_team(
    session: AsyncSession,
    team_run: TeamRun,
    team: AgentTeam,
) -> None:
    team_run.status = "running"
    await session.commit()

    start = time.time()
    sorted_steps: list[dict[str, Any]] = sorted(
        team.steps, key=lambda s: s["order"]
    )
    current_input: dict[str, Any] = dict(team_run.input)
    logs: list[dict[str, Any]] = list(team_run.logs or [])
    step_outputs: dict[str, Any] = dict(team_run.step_outputs or {})
    failed = False

    for step in sorted_steps:
        role = step.get("role", "")
        agent_id_str = step.get("agent_id", "")
        order = step.get("order", 0)
        system_prompt_override = step.get("system_prompt")

        logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": role,
                "message": f"Starting {role}...",
            }
        )
        team_run.logs = list(logs)
        await session.commit()

        # Look up AgentDefinition
        try:
            agent_uuid = uuid.UUID(agent_id_str)
        except (ValueError, AttributeError):
            logs.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "role": role,
                    "message": f"Agent id '{agent_id_str}' is invalid for role {role}",
                }
            )
            step_outputs[str(order)] = {
                "agent_id": agent_id_str,
                "role": role,
                "output": {},
                "status": "failed",
                "error": "Invalid agent_id format",
            }
            team_run.logs = list(logs)
            team_run.step_outputs = dict(step_outputs)
            await session.commit()
            failed = True
            break

        result = await session.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_uuid)
        )
        agent_def = result.scalar_one_or_none()

        if agent_def is None:
            logs.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "role": role,
                    "message": f"Agent not found for role {role} (id={agent_id_str})",
                }
            )
            step_outputs[str(order)] = {
                "agent_id": agent_id_str,
                "role": role,
                "output": {},
                "status": "failed",
                "error": "Agent not found",
            }
            team_run.logs = list(logs)
            team_run.step_outputs = dict(step_outputs)
            await session.commit()
            continue

        # Temporarily override system_prompt on the first LLM node if specified
        original_nodes = None
        if system_prompt_override:
            import copy
            original_nodes = copy.deepcopy(agent_def.nodes)
            patched_nodes = copy.deepcopy(agent_def.nodes)
            for node in patched_nodes:
                if node.get("type") == "llm":
                    node.setdefault("config", {})["system_prompt"] = system_prompt_override
                    break
            agent_def.nodes = patched_nodes

        # Create AgentRun for this step
        agent_run = AgentRun(
            agent_id=agent_def.id,
            agent_version=agent_def.version,
            status="pending",
            input=current_input,
        )
        session.add(agent_run)
        await session.commit()
        await session.refresh(agent_run)

        # Execute the agent
        await execute_agent(session, agent_run, agent_def)
        await session.refresh(agent_run)

        # Restore original nodes if we patched them
        if original_nodes is not None:
            agent_def.nodes = original_nodes
            await session.commit()

        step_outputs[str(order)] = {
            "agent_id": agent_id_str,
            "role": role,
            "output": agent_run.output or {},
            "status": agent_run.status,
        }

        logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": role,
                "message": f"{role} completed with status {agent_run.status}",
            }
        )
        team_run.logs = list(logs)
        team_run.step_outputs = dict(step_outputs)
        await session.commit()

        if agent_run.status == "failed":
            logs.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "role": role,
                    "message": f"{role} failed — aborting team run",
                }
            )
            team_run.logs = list(logs)
            await session.commit()
            failed = True
            break

        current_input = agent_run.output or {}

    team_run.output = current_input
    team_run.status = "failed" if failed else "completed"
    team_run.completed_at = datetime.now(timezone.utc)
    team_run.duration_ms = int((time.time() - start) * 1000)
    await session.commit()
