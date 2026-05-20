"""Seed the database with demo content.

Usage:
    python seed.py          # echo agent only (original behaviour)
    python seed.py --demo   # full demo: user, 3 agents, 1 team, 5 memories
"""
import argparse
import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.agent import AgentDefinition
from app.models.memory import Memory
from app.models.team import AgentTeam
from app.models.user import User

DEMO_EMAIL = "demo@dclawstack.io"
DEMO_PASSWORD = "demo-pass-1234"
DEMO_DISPLAY = "Demo User"


def _echo_agent(owner_id: uuid.UUID) -> AgentDefinition:
    return AgentDefinition(
        id=uuid.uuid4(),
        name="Echo Agent",
        description="A simple agent that echoes input through an LLM node.",
        owner_id=owner_id,
        nodes=[
            {"id": "input-1", "type": "input", "label": "User Input",
             "position": {"x": 100, "y": 200},
             "config": {"text": "Hello, world!"}},
            {"id": "llm-1", "type": "llm", "label": "LLM",
             "position": {"x": 300, "y": 200},
             "config": {"model": "llama3", "system_prompt": "You are a helpful assistant.",
                        "temperature": 0.7, "max_tokens": 256,
                        "prompt": "{{input-1.text}}"}},
            {"id": "output-1", "type": "output", "label": "Output",
             "position": {"x": 500, "y": 200}, "config": {}},
        ],
        edges=[
            {"id": "e1", "source": "input-1", "target": "llm-1"},
            {"id": "e2", "source": "llm-1", "target": "output-1"},
        ],
        entry_node_id="input-1",
        is_public=True,
    )


def _research_agent(owner_id: uuid.UUID) -> AgentDefinition:
    return AgentDefinition(
        id=uuid.uuid4(),
        name="Research Bot",
        description="Search the web for a topic, then summarise the findings.",
        owner_id=owner_id,
        nodes=[
            {"id": "input-1", "type": "input", "label": "Topic",
             "position": {"x": 100, "y": 200}, "config": {"text": "Y Combinator"}},
            {"id": "search-1", "type": "tool", "label": "Web Search",
             "position": {"x": 300, "y": 200},
             "config": {"tool_slug": "web_search", "query": "{{input-1.text}}"}},
            {"id": "llm-1", "type": "llm", "label": "Summarise",
             "position": {"x": 500, "y": 200},
             "config": {"system_prompt": "Summarise these search results.",
                        "prompt": "{{search-1.results}}"}},
            {"id": "output-1", "type": "output", "label": "Output",
             "position": {"x": 700, "y": 200}, "config": {}},
        ],
        edges=[
            {"id": "e1", "source": "input-1", "target": "search-1"},
            {"id": "e2", "source": "search-1", "target": "llm-1"},
            {"id": "e3", "source": "llm-1", "target": "output-1"},
        ],
        entry_node_id="input-1",
        is_public=True,
    )


def _calculator_agent(owner_id: uuid.UUID) -> AgentDefinition:
    return AgentDefinition(
        id=uuid.uuid4(),
        name="Quick Calculator",
        description="Evaluate a math expression via the calculator tool.",
        owner_id=owner_id,
        nodes=[
            {"id": "input-1", "type": "input", "label": "Expression",
             "position": {"x": 100, "y": 200}, "config": {"expression": "2 + 2 * 3"}},
            {"id": "calc-1", "type": "tool", "label": "Calculator",
             "position": {"x": 300, "y": 200},
             "config": {"tool_slug": "calculator", "expression": "{{input-1.expression}}"}},
            {"id": "output-1", "type": "output", "label": "Output",
             "position": {"x": 500, "y": 200}, "config": {}},
        ],
        edges=[
            {"id": "e1", "source": "input-1", "target": "calc-1"},
            {"id": "e2", "source": "calc-1", "target": "output-1"},
        ],
        entry_node_id="input-1",
        is_public=True,
    )


def _demo_team(research_id: uuid.UUID, calc_id: uuid.UUID) -> AgentTeam:
    return AgentTeam(
        id=uuid.uuid4(),
        name="Research + Math Pipeline",
        description="Run the researcher, then hand the topic to the calculator.",
        workflow_type="sequential",
        steps=[
            {"agent_id": str(research_id), "role": "researcher", "order": 1},
            {"agent_id": str(calc_id), "role": "math", "order": 2},
        ],
    )


def _demo_memories() -> list[Memory]:
    items: list[dict[str, Any]] = [
        {"key": "user_likes_dark_mode", "content": "User prefers dark mode in all UIs.",
         "memory_type": "preference", "importance": 0.8},
        {"key": "user_works_eastern", "content": "User is in US-Eastern timezone.",
         "memory_type": "preference", "importance": 0.7},
        {"key": "last_research_topic", "content": "Y Combinator W26 RFS",
         "memory_type": "episodic", "importance": 0.5},
        {"key": "model_default", "content": "Default LLM is llama3 via Ollama; fallback to OpenRouter.",
         "memory_type": "semantic", "importance": 0.9},
        {"key": "marketplace_winner", "content": "Most-installed agent: Quick Calculator.",
         "memory_type": "semantic", "importance": 0.4},
    ]
    return [
        Memory(scope="demo", key=i["key"], content=i["content"],
               memory_type=i["memory_type"], importance=i["importance"])
        for i in items
    ]


async def _get_or_create_demo_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    user = User(
        email=DEMO_EMAIL,
        display_name=DEMO_DISPLAY,
        password_hash=hash_password(DEMO_PASSWORD),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def seed_demo() -> None:
    async with AsyncSessionLocal() as session:
        user = await _get_or_create_demo_user(session)
        print(f"demo user: {user.email} (password: {DEMO_PASSWORD})")

        existing = await session.execute(
            select(AgentDefinition).where(AgentDefinition.owner_id == user.id)
        )
        if existing.scalars().first():
            print("demo agents already present — skipping creation")
            return

        echo = _echo_agent(user.id)
        research = _research_agent(user.id)
        calc = _calculator_agent(user.id)
        session.add_all([echo, research, calc])
        await session.commit()

        team = _demo_team(research.id, calc.id)
        session.add(team)
        for m in _demo_memories():
            session.add(m)
        await session.commit()
        print(f"seeded {3} agents, 1 team, {len(_demo_memories())} memories")


async def seed_echo_only() -> None:
    async with AsyncSessionLocal() as session:
        owner_id = uuid.uuid4()
        agent = _echo_agent(owner_id)
        session.add(agent)
        await session.commit()
        print(f"Seeded agent {agent.id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true",
                        help="Seed a full demo dataset (user, agents, team, memories).")
    args = parser.parse_args()
    if args.demo:
        asyncio.run(seed_demo())
    else:
        asyncio.run(seed_echo_only())


if __name__ == "__main__":
    main()
