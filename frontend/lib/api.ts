const BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err);
  }
  return res.json() as Promise<T>;
}

export type AgentNode = {
  id: string;
  type: "llm" | "tool" | "memory" | "condition" | "loop" | "input" | "output";
  label: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
};

export type AgentEdge = {
  id: string;
  source: string;
  target: string;
  condition?: string;
};

export type AgentDefinition = {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  nodes: AgentNode[];
  edges: AgentEdge[];
  entry_node_id: string;
  max_steps: number;
  timeout_seconds: number;
  is_public: boolean;
  version: number;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: string;
  agent_id: string;
  agent_version: number;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  step_count: number;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  created_at: string;
};

export async function listAgents(): Promise<AgentDefinition[]> {
  return fetchJson<AgentDefinition[]>("/api/v1/agent/agents");
}

export async function getAgent(id: string): Promise<AgentDefinition> {
  return fetchJson<AgentDefinition>(`/api/v1/agent/agents/${id}`);
}

export async function createAgent(payload: {
  name: string;
  description?: string;
  nodes: AgentNode[];
  edges: AgentEdge[];
  entry_node_id: string;
}): Promise<AgentDefinition> {
  return fetchJson<AgentDefinition>("/api/v1/agent/agents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteAgent(id: string): Promise<void> {
  await fetchJson<void>(`/api/v1/agent/agents/${id}`, { method: "DELETE" });
}

export async function createRun(
  agentId: string,
  input: Record<string, unknown>
): Promise<AgentRun> {
  return fetchJson<AgentRun>(`/api/v1/agent/agents/${agentId}/runs`, {
    method: "POST",
    body: JSON.stringify({ input, wait_for_completion: false }),
  });
}

export async function getRun(id: string): Promise<AgentRun> {
  return fetchJson<AgentRun>(`/api/v1/agent/runs/${id}`);
}

export async function listMarketplace(): Promise<
  { id: string; name: string; description?: string; owner_name: string; install_count: number }[]
> {
  return fetchJson("/api/v1/agent/marketplace");
}
