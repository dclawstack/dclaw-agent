"use client";

import { useEffect, useState } from "react";
import { listAgents, getRun, type AgentDefinition, type AgentRun } from "@/lib/api";

export default function RunsPage() {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const ags = await listAgents();
      setAgents(ags);
      const allRuns: AgentRun[] = [];
      for (const a of ags) {
        // Runs are nested in agent API; fetch individually for simplicity
      }
      // For MVP, we don't have a list-runs endpoint; skip loading runs
      setLoading(false);
    }
    load();
  }, []);

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Run History</h1>
      <p className="text-gray-500">Run history is available per agent in the Test Studio.</p>
    </main>
  );
}
