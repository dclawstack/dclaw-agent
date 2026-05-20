"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  listAgents,
  listRuns,
  type AgentDefinition,
  type AgentRunSummary,
} from "@/lib/api";

const STATUSES = ["", "pending", "running", "completed", "failed", "cancelled"] as const;

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-gray-200 text-gray-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-yellow-100 text-yellow-800",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, a] = await Promise.all([
        listRuns({
          status: statusFilter || undefined,
          agent_id: agentFilter || undefined,
          limit: 100,
        }),
        listAgents(),
      ]);
      setRuns(r);
      setAgents(a);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, agentFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const agentName = (id: string) =>
    agents.find((a) => a.id === id)?.name || id.slice(0, 8);

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Run History</h1>
        <button
          onClick={load}
          className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded"
        >
          Refresh
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded px-2 py-1"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s || "All statuses"}
            </option>
          ))}
        </select>
        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="border rounded px-2 py-1"
        >
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mb-4 text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading runs…</p>
      ) : runs.length === 0 ? (
        <p className="text-gray-500">No runs match these filters.</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-left text-sm text-gray-600 border-b">
              <th className="py-2 pr-2">Run ID</th>
              <th className="py-2 pr-2">Agent</th>
              <th className="py-2 pr-2">Status</th>
              <th className="py-2 pr-2">Started</th>
              <th className="py-2 pr-2">Duration</th>
              <th className="py-2 pr-2">Steps</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="border-b text-sm hover:bg-gray-50">
                <td className="py-2 pr-2 font-mono text-xs">
                  <Link href={`/runs/${r.id}`} className="text-blue-600 hover:underline">
                    {r.id.slice(0, 8)}
                  </Link>
                </td>
                <td className="py-2 pr-2">{agentName(r.agent_id)}</td>
                <td className="py-2 pr-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      STATUS_COLOR[r.status] || "bg-gray-100"
                    }`}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="py-2 pr-2 text-gray-700">
                  {new Date(r.started_at).toLocaleString()}
                </td>
                <td className="py-2 pr-2 text-gray-700">
                  {r.duration_ms != null ? `${r.duration_ms} ms` : "—"}
                </td>
                <td className="py-2 pr-2 text-gray-700">{r.step_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
