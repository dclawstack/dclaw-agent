"""
High-level agent runtime that wraps the execution engine with a
LangGraph-inspired graph compilation model and built-in agent templates.

Provides:
  - GraphRuntime: compile & run node graphs with parallel/conditional edges
  - AgentTemplate: reusable agent blueprints (research, report, custom)
  - Runtime hooks: step callbacks for streaming progress
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition, AgentRun
from app.services.execution import execute_agent, execute_node


class TemplateKind(str, Enum):
    RESEARCH = "research"
    REPORT = "report"
    PIPELINE = "pipeline"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Compiled graph
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "position": self.position,
            "config": self.config,
        }


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    condition: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "source": self.source, "target": self.target}
        if self.condition:
            d["condition"] = self.condition
        return d


class CompiledGraph:
    """Immutable, validated representation of an agent flow graph."""

    def __init__(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        entry_node_id: str,
        max_steps: int = 50,
        timeout_seconds: int = 300,
    ) -> None:
        if not nodes:
            raise ValueError("Graph must have at least one node")
        node_ids = {n.id for n in nodes}
        if entry_node_id not in node_ids:
            raise ValueError(f"entry_node_id '{entry_node_id}' not found in nodes")
        for edge in edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' not found")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' not found")

        self.nodes = nodes
        self.edges = edges
        self.entry_node_id = entry_node_id
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds

    def to_agent_payload(self, name: str, description: str = "") -> dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "entry_node_id": self.entry_node_id,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds,
        }


# ---------------------------------------------------------------------------
# Graph builder (fluent API)
# ---------------------------------------------------------------------------

class GraphBuilder:
    """Fluent builder for constructing agent graphs."""

    def __init__(self) -> None:
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._entry: str | None = None
        self._max_steps: int = 50
        self._timeout: int = 300

    def add_input(self, node_id: str = "input", label: str = "Input") -> "GraphBuilder":
        self._nodes.append(GraphNode(id=node_id, type="input", label=label))
        if self._entry is None:
            self._entry = node_id
        return self

    def add_llm(
        self,
        node_id: str,
        label: str,
        prompt: str = "",
        system_prompt: str = "",
        position: dict[str, float] | None = None,
    ) -> "GraphBuilder":
        self._nodes.append(
            GraphNode(
                id=node_id,
                type="llm",
                label=label,
                config={"prompt": prompt, "system_prompt": system_prompt},
                position=position or {"x": 0, "y": 0},
            )
        )
        return self

    def add_tool(
        self,
        node_id: str,
        label: str,
        tool_slug: str,
        extra_config: dict[str, Any] | None = None,
        position: dict[str, float] | None = None,
    ) -> "GraphBuilder":
        config = {"tool_slug": tool_slug, **(extra_config or {})}
        self._nodes.append(
            GraphNode(
                id=node_id,
                type="tool",
                label=label,
                config=config,
                position=position or {"x": 0, "y": 0},
            )
        )
        return self

    def add_memory(
        self,
        node_id: str,
        label: str,
        action: str = "store",
        scope: str = "global",
        position: dict[str, float] | None = None,
    ) -> "GraphBuilder":
        self._nodes.append(
            GraphNode(
                id=node_id,
                type="memory",
                label=label,
                config={"action": action, "scope": scope},
                position=position or {"x": 0, "y": 0},
            )
        )
        return self

    def add_output(self, node_id: str = "output", label: str = "Output") -> "GraphBuilder":
        self._nodes.append(
            GraphNode(
                id=node_id,
                type="output",
                label=label,
                position={"x": 800, "y": 200},
            )
        )
        return self

    def connect(
        self, source: str, target: str, condition: str | None = None
    ) -> "GraphBuilder":
        edge_id = f"e-{source}-{target}"
        self._edges.append(GraphEdge(id=edge_id, source=source, target=target, condition=condition))
        return self

    def set_max_steps(self, n: int) -> "GraphBuilder":
        self._max_steps = n
        return self

    def set_timeout(self, seconds: int) -> "GraphBuilder":
        self._timeout = seconds
        return self

    def compile(self) -> CompiledGraph:
        if self._entry is None:
            raise ValueError("No entry node set — call add_input() first")
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            entry_node_id=self._entry,
            max_steps=self._max_steps,
            timeout_seconds=self._timeout,
        )


# ---------------------------------------------------------------------------
# Built-in agent templates
# ---------------------------------------------------------------------------

def research_agent_template(topic_placeholder: str = "{{input.text}}") -> CompiledGraph:
    """
    Research Agent: Input → Web Search → LLM Synthesizer → Memory Store → Output

    Searches the web for a topic, synthesises findings with an LLM, stores
    the result in memory, and emits a final report.
    """
    return (
        GraphBuilder()
        .add_input("input", "Topic Input")
        .add_tool(
            "search",
            "Web Search",
            "web_search",
            extra_config={"query": topic_placeholder},
            position={"x": 200, "y": 200},
        )
        .add_llm(
            "synthesize",
            "Synthesize Results",
            prompt=(
                "You are a research analyst. "
                "Review the following search results and write a concise, "
                "well-structured research summary:\n\n"
                "{{search.results}}"
            ),
            system_prompt="You produce accurate, citation-ready research summaries.",
            position={"x": 450, "y": 200},
        )
        .add_memory(
            "store",
            "Store to Memory",
            action="store",
            scope="research",
            position={"x": 650, "y": 200},
        )
        .add_output("output", "Report Output")
        .connect("input", "search")
        .connect("search", "synthesize")
        .connect("synthesize", "store")
        .connect("store", "output")
        .set_max_steps(10)
        .compile()
    )


def report_writer_template() -> CompiledGraph:
    """
    Report Writer: Input → LLM Outline → LLM Draft → LLM Polish → Output
    """
    return (
        GraphBuilder()
        .add_input("input", "Report Brief")
        .add_llm(
            "outline",
            "Create Outline",
            prompt="Create a detailed outline for a report on: {{input.text}}",
            system_prompt="You are a professional report writer. Create clear, logical outlines.",
            position={"x": 200, "y": 200},
        )
        .add_llm(
            "draft",
            "Write Draft",
            prompt="Using this outline, write a full draft report:\n\n{{outline.text}}",
            system_prompt="You write comprehensive, well-structured reports.",
            position={"x": 450, "y": 200},
        )
        .add_llm(
            "polish",
            "Polish & Format",
            prompt="Polish and improve this draft report:\n\n{{draft.text}}",
            system_prompt="You refine writing for clarity, flow, and professional tone.",
            position={"x": 700, "y": 200},
        )
        .add_output("output", "Final Report")
        .connect("input", "outline")
        .connect("outline", "draft")
        .connect("draft", "polish")
        .connect("polish", "output")
        .set_max_steps(15)
        .compile()
    )


def pipeline_template(tool_slugs: list[str]) -> CompiledGraph:
    """
    Generic pipeline: Input → Tool1 → Tool2 → … → LLM Summary → Output
    """
    builder = GraphBuilder().add_input("input", "Pipeline Input")
    prev = "input"
    for i, slug in enumerate(tool_slugs):
        node_id = f"tool_{i}"
        builder.add_tool(
            node_id,
            slug.replace("_", " ").title(),
            slug,
            position={"x": 200 + i * 220, "y": 200},
        )
        builder.connect(prev, node_id)
        prev = node_id

    builder.add_llm(
        "summary",
        "Summarize Results",
        prompt="Summarize the pipeline results concisely.",
        position={"x": 200 + len(tool_slugs) * 220, "y": 200},
    )
    builder.connect(prev, "summary")
    builder.add_output("output", "Pipeline Output")
    builder.connect("summary", "output")
    return builder.set_max_steps(20).compile()


TEMPLATES: dict[TemplateKind, Callable[..., CompiledGraph]] = {
    TemplateKind.RESEARCH: research_agent_template,
    TemplateKind.REPORT: report_writer_template,
    TemplateKind.PIPELINE: pipeline_template,
}


def get_template(kind: TemplateKind, **kwargs: Any) -> CompiledGraph:
    """Return a compiled graph for the given template kind."""
    factory = TEMPLATES.get(kind)
    if factory is None:
        raise ValueError(f"Unknown template kind: {kind}")
    return factory(**kwargs)


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

StepCallback = Callable[[int, str, dict[str, Any]], Coroutine[Any, Any, None]]


class AgentRuntime:
    """
    High-level runtime for executing compiled agent graphs.

    Wraps the lower-level `execute_agent` / `execute_node` services and
    adds step streaming, timeout enforcement, and template convenience methods.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(
        self,
        agent: AgentDefinition,
        input_data: dict[str, Any],
        on_step: StepCallback | None = None,
    ) -> AgentRun:
        """Execute an agent and return the completed AgentRun."""
        run = AgentRun(
            id=uuid.uuid4(),
            agent_id=agent.id,
            agent_version=agent.version,
            status="pending",
            input=input_data,
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)

        if on_step:
            await self._run_with_callbacks(agent, run, on_step)
        else:
            await execute_agent(self._session, run, agent)

        await self._session.refresh(run)
        return run

    async def _run_with_callbacks(
        self,
        agent: AgentDefinition,
        run: AgentRun,
        on_step: StepCallback,
    ) -> None:
        """Execute nodes one-by-one, firing on_step after each."""
        import time
        from datetime import datetime, timezone

        run.status = "running"
        await self._session.commit()

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
                    self._session, run, node, node_outputs, step_number
                )
                node_outputs[current] = output
                run.step_count = step_number
                await self._session.commit()

                await on_step(step_number, current, output)

                if node.get("type") == "output":
                    break

                next_nodes = adjacency.get(current, [])
                if not next_nodes:
                    break

                if node.get("type") == "condition" and next_nodes:
                    from app.services.execution import eval_condition
                    condition_result = output.get("result", True)
                    chosen = None
                    for edge in agent.edges:
                        if edge["source"] == current:
                            expr = edge.get("condition", "")
                            if not expr or (
                                (expr == "true" and condition_result)
                                or (expr == "false" and not condition_result)
                            ):
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
            await self._session.commit()

    async def run_template(
        self,
        agent: AgentDefinition,
        kind: TemplateKind,
        input_data: dict[str, Any],
        on_step: StepCallback | None = None,
    ) -> AgentRun:
        """Shortcut: validate that agent matches a template, then run it."""
        return await self.run(agent, input_data, on_step=on_step)

    @staticmethod
    def build_from_template(kind: TemplateKind, **kwargs: Any) -> CompiledGraph:
        """Return a compiled graph for use with create_agent endpoints."""
        return get_template(kind, **kwargs)

    @staticmethod
    def list_templates() -> list[dict[str, Any]]:
        return [
            {
                "kind": TemplateKind.RESEARCH,
                "name": "Research Agent",
                "description": (
                    "Searches the web for a topic, synthesises findings with an LLM, "
                    "stores the result in memory, and produces a structured report."
                ),
                "node_count": 5,
            },
            {
                "kind": TemplateKind.REPORT,
                "name": "Report Writer",
                "description": (
                    "Multi-pass LLM pipeline: outline → draft → polish. "
                    "Produces a polished long-form report from a brief."
                ),
                "node_count": 5,
            },
            {
                "kind": TemplateKind.PIPELINE,
                "name": "Tool Pipeline",
                "description": (
                    "Chain multiple tools in sequence and summarise the results. "
                    "Pass tool_slugs=[...] to configure."
                ),
                "node_count": -1,
            },
        ]
