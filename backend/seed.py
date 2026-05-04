import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.agent import AgentDefinition


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        agent = AgentDefinition(
            id=uuid4(),
            name="Echo Agent",
            description="A simple agent that echoes input through an LLM node.",
            owner_id=uuid4(),
            nodes=[
                {
                    "id": "input-1",
                    "type": "input",
                    "label": "User Input",
                    "position": {"x": 100, "y": 200},
                    "config": {"text": "Hello, world!"},
                },
                {
                    "id": "llm-1",
                    "type": "llm",
                    "label": "LLM",
                    "position": {"x": 300, "y": 200},
                    "config": {
                        "model": "llama3",
                        "system_prompt": "You are a helpful assistant.",
                        "temperature": 0.7,
                        "max_tokens": 256,
                        "prompt": "{{input-1.text}}",
                    },
                },
                {
                    "id": "output-1",
                    "type": "output",
                    "label": "Output",
                    "position": {"x": 500, "y": 200},
                    "config": {},
                },
            ],
            edges=[
                {"id": "e1", "source": "input-1", "target": "llm-1"},
                {"id": "e2", "source": "llm-1", "target": "output-1"},
            ],
            entry_node_id="input-1",
            max_steps=50,
            timeout_seconds=300,
            is_public=True,
            version=1,
        )
        session.add(agent)
        await session.commit()
        print(f"Seeded agent {agent.id}")


if __name__ == "__main__":
    asyncio.run(seed())
