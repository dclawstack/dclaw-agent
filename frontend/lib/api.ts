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

export type Tool = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  category: string;
  config_schema: Record<string, string>;
  is_builtin: boolean;
  is_installed: boolean;
  created_at: string;
  updated_at: string;
};

export async function listTools(): Promise<Tool[]> {
  return fetchJson<Tool[]>("/api/v1/agent/tools");
}

export async function installTool(slug: string): Promise<Tool> {
  return fetchJson<Tool>(`/api/v1/agent/tools/${slug}/install`, {
    method: "POST",
  });
}

export async function uninstallTool(slug: string): Promise<void> {
  await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/agent/tools/${slug}/install`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
}

export async function executeTool(
  slug: string,
  inputs: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return fetchJson<Record<string, unknown>>(
    `/api/v1/agent/tools/${slug}/execute`,
    {
      method: "POST",
      body: JSON.stringify({ inputs }),
    }
  );
}

export type TeamStep = {
  agent_id: string;
  role: string;
  order: number;
  system_prompt?: string;
};

export type AgentTeam = {
  id: string;
  name: string;
  description: string | null;
  workflow_type: string;
  steps: TeamStep[];
  created_at: string;
  updated_at: string;
};

export type TeamRunLog = {
  timestamp: string;
  role: string;
  message: string;
};

export type TeamRun = {
  id: string;
  team_id: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  step_outputs: Record<string, unknown>;
  logs: TeamRunLog[];
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
};

export async function listTeams(): Promise<AgentTeam[]> {
  return fetchJson<AgentTeam[]>("/api/v1/agent/teams");
}

export async function createTeam(payload: {
  name: string;
  description?: string;
  workflow_type?: string;
  steps: TeamStep[];
}): Promise<AgentTeam> {
  return fetchJson<AgentTeam>("/api/v1/agent/teams", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteTeam(id: string): Promise<void> {
  await fetchJson<void>(`/api/v1/agent/teams/${id}`, { method: "DELETE" });
}

export async function createTeamRun(
  teamId: string,
  payload: { input: Record<string, unknown>; wait_for_completion?: boolean }
): Promise<TeamRun> {
  return fetchJson<TeamRun>(`/api/v1/agent/teams/${teamId}/runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTeamRun(runId: string): Promise<TeamRun> {
  return fetchJson<TeamRun>(`/api/v1/agent/teams/runs/${runId}`);
}

export type Memory = {
  id: string;
  scope: string;
  memory_type: "episodic" | "semantic" | "preference";
  key: string;
  content: string;
  metadata: Record<string, unknown>;
  importance: number;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string;
  updated_at: string;
};

export async function listMemories(scope?: string, memoryType?: string): Promise<Memory[]> {
  const params = new URLSearchParams();
  if (scope !== undefined) params.set("scope", scope);
  if (memoryType !== undefined) params.set("memory_type", memoryType);
  const qs = params.toString();
  return fetchJson<Memory[]>(`/api/v1/agent/memories${qs ? `?${qs}` : ""}`);
}

export async function createMemory(payload: {
  scope?: string;
  memory_type?: string;
  key: string;
  content: string;
  metadata?: Record<string, unknown>;
  importance?: number;
}): Promise<Memory> {
  return fetchJson<Memory>("/api/v1/agent/memories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMemory(
  id: string,
  payload: { content?: string; importance?: number }
): Promise<Memory> {
  return fetchJson<Memory>(`/api/v1/agent/memories/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteMemory(id: string): Promise<void> {
  await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/agent/memories/${id}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
}

export async function retrieveMemories(payload: {
  scope?: string;
  query: string;
  top_k?: number;
}): Promise<Memory[]> {
  return fetchJson<Memory[]>("/api/v1/agent/memories/retrieve", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
