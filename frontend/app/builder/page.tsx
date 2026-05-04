"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import type { Node, Edge } from "@xyflow/react";
import FlowCanvas from "@/components/flow/FlowCanvas";
import NodePalette from "@/components/flow/NodePalette";
import PropertyPanel from "@/components/flow/PropertyPanel";
import { getAgent, createAgent, createRun, type AgentDefinition } from "@/lib/api";

function BuilderInner() {
  const searchParams = useSearchParams();
  const agentId = searchParams.get("agentId");

  const [name, setName] = useState("Untitled Agent");
  const [description, setDescription] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [savedAgent, setSavedAgent] = useState<AgentDefinition | null>(null);

  useEffect(() => {
    if (agentId) {
      getAgent(agentId).then((agent) => {
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
      });
    }
  }, [agentId]);

  const handleNodeSelect = useCallback((node: Node | null) => {
    setSelectedNode(node);
  }, []);

  function handlePropertyChange(updated: Node) {
    setNodes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
    setSelectedNode(updated);
  }

  async function handleSave() {
    const entry = nodes.find((n) => n.type === "input")?.id || "";
    const payload = {
      name,
      description,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type as any,
        label: String(n.data?.label || n.type),
        position: n.position,
        config: (n.data?.config as Record<string, unknown>) || {},
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        condition: (e.label as string) || undefined,
      })),
      entry_node_id: entry,
    };
    const agent = await createAgent(payload);
    setSavedAgent(agent);
    alert(`Saved agent ${agent.id}`);
  }

  async function handleRun() {
    if (!savedAgent && !agentId) {
      alert("Save the agent first");
      return;
    }
    const id = savedAgent?.id || agentId!;
    const run = await createRun(id, { text: "Hello from builder" });
    alert(`Run started: ${run.id}`);
  }

  return (
    <main className="h-screen flex flex-col">
      <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          <input
            className="text-lg font-semibold border rounded px-2 py-1"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="text-sm text-gray-500 border rounded px-2 py-1"
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-brand text-white rounded-lg hover:opacity-90"
          >
            Save
          </button>
          <button
            onClick={handleRun}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Run
          </button>
        </div>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <NodePalette />
        <div className="flex-1 relative">
          <FlowCanvas
            initialNodes={nodes}
            initialEdges={edges}
            onNodesChange={setNodes}
            onEdgesChange={setEdges}
            onNodeSelect={handleNodeSelect}
          />
        </div>
        <PropertyPanel selected={selectedNode} onChange={handlePropertyChange} />
      </div>
    </main>
  );
}

export default function BuilderPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading builder...</div>}>
      <BuilderInner />
    </Suspense>
  );
}
