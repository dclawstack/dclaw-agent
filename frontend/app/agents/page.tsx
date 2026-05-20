"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAgents, createAgent, deleteAgent, createRun, type AgentDefinition } from "@/lib/api";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    await deleteAgent(id);
    setAgents((prev) => prev.filter((a) => a.id !== id));
  }

  async function handleQuickRun(agent: AgentDefinition) {
    const run = await createRun(agent.id, { text: "Hello" });
    alert(`Run started: ${run.id}`);
  }

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Agents</h1>
        <Link
          href="/agents/builder"
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          + New Agent
        </Link>
      </div>
      {loading ? (
        <p>Loading...</p>
      ) : agents.length === 0 ? (
        <p className="text-gray-500">No agents yet. Create one!</p>
      ) : (
        <div className="space-y-3">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-100"
            >
              <div>
                <h2 className="font-semibold">{agent.name}</h2>
                <p className="text-sm text-gray-500">{agent.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleQuickRun(agent)}
                  className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Run
                </button>
                <Link
                  href={`/agents/builder?agentId=${agent.id}`}
                  className="px-3 py-1.5 text-sm bg-gray-100 rounded hover:bg-gray-200"
                >
                  Edit
                </Link>
                <button
                  onClick={() => handleDelete(agent.id)}
                  className="px-3 py-1.5 text-sm bg-red-50 text-red-600 rounded hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
