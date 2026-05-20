"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { Node, Edge } from "@xyflow/react";
import FlowCanvas from "@/components/flow/FlowCanvas";
import NodePalette from "@/components/flow/NodePalette";
import PropertyPanel from "@/components/flow/PropertyPanel";
import {
  getAgent,
  createAgent,
  createRun,
  listTools,
  type AgentDefinition,
  type AgentNode,
  type AgentEdge,
  type Tool,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Agent templates matching backend TemplateKind
// ---------------------------------------------------------------------------

type TemplateKind = "research" | "report" | "pipeline" | "custom";

interface TemplateConfig {
  kind: TemplateKind;
  name: string;
  description: string;
  nodes: AgentNode[];
  edges: AgentEdge[];
  entry_node_id: string;
}

const TEMPLATES: TemplateConfig[] = [
  {
    kind: "research",
    name: "Research Agent",
    description:
      "Searches the web for a topic, synthesises findings with an LLM, stores the result in memory, and produces a structured report.",
    entry_node_id: "input",
    nodes: [
      { id: "input", type: "input", label: "Topic Input", position: { x: 50, y: 200 }, config: {} },
      {
        id: "search",
        type: "tool",
        label: "Web Search",
        position: { x: 260, y: 200 },
        config: { tool_slug: "web_search", query: "{{input.text}}" },
      },
      {
        id: "synthesize",
        type: "llm",
        label: "Synthesize Results",
        position: { x: 500, y: 200 },
        config: {
          prompt:
            "You are a research analyst. Review the following search results and write a concise, well-structured research summary:\n\n{{search.results}}",
          system_prompt: "You produce accurate, citation-ready research summaries.",
        },
      },
      {
        id: "store",
        type: "memory",
        label: "Store to Memory",
        position: { x: 740, y: 200 },
        config: { action: "store", scope: "research" },
      },
      { id: "output", type: "output", label: "Report Output", position: { x: 980, y: 200 }, config: {} },
    ],
    edges: [
      { id: "e-input-search", source: "input", target: "search" },
      { id: "e-search-synthesize", source: "search", target: "synthesize" },
      { id: "e-synthesize-store", source: "synthesize", target: "store" },
      { id: "e-store-output", source: "store", target: "output" },
    ],
  },
  {
    kind: "report",
    name: "Report Writer",
    description:
      "Multi-pass LLM pipeline: outline → draft → polish. Produces a polished long-form report from a brief.",
    entry_node_id: "input",
    nodes: [
      { id: "input", type: "input", label: "Report Brief", position: { x: 50, y: 200 }, config: {} },
      {
        id: "outline",
        type: "llm",
        label: "Create Outline",
        position: { x: 270, y: 200 },
        config: {
          prompt: "Create a detailed outline for a report on: {{input.text}}",
          system_prompt: "You are a professional report writer. Create clear, logical outlines.",
        },
      },
      {
        id: "draft",
        type: "llm",
        label: "Write Draft",
        position: { x: 520, y: 200 },
        config: {
          prompt: "Using this outline, write a full draft report:\n\n{{outline.text}}",
          system_prompt: "You write comprehensive, well-structured reports.",
        },
      },
      {
        id: "polish",
        type: "llm",
        label: "Polish & Format",
        position: { x: 770, y: 200 },
        config: {
          prompt: "Polish and improve this draft report:\n\n{{draft.text}}",
          system_prompt: "You refine writing for clarity, flow, and professional tone.",
        },
      },
      { id: "output", type: "output", label: "Final Report", position: { x: 1020, y: 200 }, config: {} },
    ],
    edges: [
      { id: "e-input-outline", source: "input", target: "outline" },
      { id: "e-outline-draft", source: "outline", target: "draft" },
      { id: "e-draft-polish", source: "draft", target: "polish" },
      { id: "e-polish-output", source: "polish", target: "output" },
    ],
  },
  {
    kind: "custom",
    name: "Blank Canvas",
    description: "Start from scratch and build your own agent flow.",
    entry_node_id: "input",
    nodes: [
      { id: "input", type: "input", label: "Input", position: { x: 100, y: 200 }, config: {} },
      { id: "output", type: "output", label: "Output", position: { x: 600, y: 200 }, config: {} },
    ],
    edges: [],
  },
];

// ---------------------------------------------------------------------------
// Template Picker overlay
// ---------------------------------------------------------------------------

function TemplatePicker({ onSelect }: { onSelect: (t: TemplateConfig) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-2xl w-full mx-4">
        <h2 className="text-2xl font-bold mb-2">Choose a Template</h2>
        <p className="text-gray-500 mb-6 text-sm">
          Pick a starting point for your agent. You can customise it on the canvas.
        </p>
        <div className="grid grid-cols-1 gap-4">
          {TEMPLATES.map((t) => (
            <button
              key={t.kind}
              onClick={() => onSelect(t)}
              className="text-left p-5 rounded-xl border-2 border-gray-100 hover:border-indigo-400 hover:bg-indigo-50 transition group"
            >
              <div className="flex items-start gap-4">
                <span className="text-3xl select-none">
                  {t.kind === "research" ? "🔍" : t.kind === "report" ? "📝" : "⚡"}
                </span>
                <div>
                  <h3 className="font-semibold text-gray-900 group-hover:text-indigo-700">
                    {t.name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-0.5">{t.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run status panel
// ---------------------------------------------------------------------------

function RunPanel({
  run,
  onClose,
}: {
  run: { id: string; status: string; output?: Record<string, unknown> } | null;
  onClose: () => void;
}) {
  if (!run) return null;
  return (
    <div className="absolute bottom-4 right-4 z-40 w-80 bg-white rounded-xl shadow-xl border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm">Latest Run</span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xs">
          ✕
        </button>
      </div>
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            run.status === "completed"
              ? "bg-green-100 text-green-700"
              : run.status === "failed"
              ? "bg-red-100 text-red-700"
              : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {run.status}
        </span>
        <span className="text-xs text-gray-400 truncate">{run.id}</span>
      </div>
      {run.output && (
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-auto max-h-48 text-gray-700">
          {JSON.stringify(run.output, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main builder inner component
// ---------------------------------------------------------------------------

function AgentBuilderInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const agentId = searchParams.get("agentId");

  const [showPicker, setShowPicker] = useState(!agentId);
  const [name, setName] = useState("Untitled Agent");
  const [description, setDescription] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [savedAgent, setSavedAgent] = useState<AgentDefinition | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [latestRun, setLatestRun] = useState<{
    id: string;
    status: string;
    output?: Record<string, unknown>;
  } | null>(null);
  const [tools, setTools] = useState<Tool[]>([]);

  useEffect(() => {
    listTools().then(setTools).catch(() => {});
  }, []);

  useEffect(() => {
    if (agentId) {
      getAgent(agentId)
        .then((agent) => {
          setName(agent.name);
          setDescription(agent.description || "");
          setNodes(
            agent.nodes.map((n) => ({
              id: n.id,
              type: n.type,
              position: n.position,
              data: { label: n.label, config: n.config },
            }))
          );
          setEdges(
            agent.edges.map((e) => ({
              id: e.id,
              source: e.source,
              target: e.target,
              label: e.condition,
            }))
          );
          setSavedAgent(agent);
        })
        .catch(console.error);
    }
  }, [agentId]);

  function applyTemplate(tmpl: TemplateConfig) {
    setName(tmpl.name);
    setDescription(tmpl.description);
    setNodes(
      tmpl.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: { label: n.label, config: n.config },
      }))
    );
    setEdges(
      tmpl.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      }))
    );
    setShowPicker(false);
  }

  const handleNodeSelect = useCallback((node: Node | null) => {
    setSelectedNode(node);
  }, []);

  function handlePropertyChange(updated: Node) {
    setNodes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
    setSelectedNode(updated);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const entry = nodes.find((n) => n.type === "input")?.id ?? "";
      const payload = {
        name,
        description,
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type as AgentNode["type"],
          label: String(n.data?.label ?? n.type),
          position: n.position,
          config: (n.data?.config as Record<string, unknown>) ?? {},
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          condition: (e.label as string) ?? undefined,
        })),
        entry_node_id: entry,
      };
      const agent = await createAgent(payload);
      setSavedAgent(agent);
    } catch (err) {
      alert(`Save failed: ${err}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleRun() {
    const id = savedAgent?.id ?? agentId;
    if (!id) {
      alert("Save the agent first");
      return;
    }
    setRunning(true);
    try {
      const run = await createRun(id, { text: "Hello from agent builder" });
      setLatestRun({ id: run.id, status: run.status, output: run.output ?? undefined });
    } catch (err) {
      alert(`Run failed: ${err}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      {showPicker && <TemplatePicker onSelect={applyTemplate} />}

      <main className="h-screen flex flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/agents")}
              className="text-sm text-gray-400 hover:text-gray-600 mr-1"
              title="Back to Agents"
            >
              ← Agents
            </button>
            <input
              className="text-lg font-semibold border rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="text-sm text-gray-400 border rounded-lg px-3 py-1.5 w-64 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPicker(true)}
              className="px-3 py-1.5 text-sm text-gray-600 border rounded-lg hover:bg-gray-50"
            >
              Templates
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-60 text-sm font-medium"
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={handleRun}
              disabled={running || (!savedAgent && !agentId)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-60 text-sm font-medium"
              title={!savedAgent && !agentId ? "Save first" : undefined}
            >
              {running ? "Running…" : "Run"}
            </button>
          </div>
        </header>

        {/* Canvas area */}
        <div className="flex-1 flex overflow-hidden relative">
          <NodePalette />
          <div className="flex-1 relative">
            <FlowCanvas
              initialNodes={nodes}
              initialEdges={edges}
              onNodesChange={setNodes}
              onEdgesChange={setEdges}
              onNodeSelect={handleNodeSelect}
            />
            <RunPanel run={latestRun} onClose={() => setLatestRun(null)} />
          </div>
          <PropertyPanel selected={selectedNode} onChange={handlePropertyChange} />
        </div>

        {/* Available tools hint */}
        {tools.length > 0 && (
          <div className="px-4 py-1.5 bg-gray-50 border-t border-gray-100 text-xs text-gray-400 flex gap-2 flex-wrap">
            <span className="font-medium text-gray-500">Tools:</span>
            {tools.map((t) => (
              <span key={t.slug} className="bg-white border border-gray-200 rounded px-1.5 py-0.5">
                {t.name}
              </span>
            ))}
          </div>
        )}
      </main>
    </>
  );
}

export default function AgentBuilderPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-500">Loading builder…</div>}>
      <AgentBuilderInner />
    </Suspense>
  );
}
