"use client";

import { useEffect, useState } from "react";
import {
  listTeams,
  listAgents,
  createTeam,
  deleteTeam,
  createTeamRun,
  listTeamRuns,
  AgentTeam,
  AgentDefinition,
  TeamStep,
  TeamRun,
} from "@/lib/api";

const ROLE_COLORS: Record<string, string> = {
  researcher: "bg-blue-100 border-blue-400 text-blue-800",
  writer: "bg-green-100 border-green-400 text-green-800",
  reviewer: "bg-yellow-100 border-yellow-400 text-yellow-800",
  publisher: "bg-purple-100 border-purple-400 text-purple-800",
};

const STEP_COLORS = [
  "bg-blue-100 border-blue-400 text-blue-800",
  "bg-green-100 border-green-400 text-green-800",
  "bg-yellow-100 border-yellow-400 text-yellow-800",
  "bg-purple-100 border-purple-400 text-purple-800",
  "bg-red-100 border-red-400 text-red-800",
];

const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700 animate-pulse",
  pending: "bg-gray-100 text-gray-600",
};

const STATUS_DOT: Record<string, string> = {
  completed: "bg-green-500",
  failed: "bg-red-500",
  running: "bg-blue-500 animate-pulse",
  pending: "bg-gray-400",
};

type FormStep = { role: string; agent_id: string };

function WorkflowPipeline({
  steps,
  stepOutputs,
  isRunning,
}: {
  steps: TeamStep[];
  stepOutputs?: Record<string, unknown>;
  isRunning?: boolean;
}) {
  const sorted = [...steps].sort((a, b) => a.order - b.order);
  return (
    <div className="flex items-center gap-1 flex-wrap my-3">
      {sorted.map((step, idx) => {
        const out = stepOutputs?.[String(step.order)] as
          | { status?: string }
          | undefined;
        const status = out?.status;
        const colorKey = step.role.toLowerCase();
        const colorClass =
          ROLE_COLORS[colorKey] ?? STEP_COLORS[idx % STEP_COLORS.length];
        return (
          <div key={idx} className="flex items-center gap-1">
            <div
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold ${colorClass}`}
            >
              {status && (
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    STATUS_DOT[status] ?? "bg-gray-400"
                  }`}
                />
              )}
              {isRunning && !status && (
                <span className="w-2 h-2 rounded-full shrink-0 bg-gray-300" />
              )}
              <span>
                {idx + 1}. {step.role}
              </span>
            </div>
            {idx < sorted.length - 1 && (
              <svg
                className="text-gray-400 shrink-0"
                width="18"
                height="18"
                viewBox="0 0 18 18"
                fill="none"
              >
                <path
                  d="M4 9h10M10 5l4 4-4 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ChatLog({ logs }: { logs: { timestamp: string; role: string; message: string }[] }) {
  if (!logs.length) return null;
  return (
    <div className="mt-3 bg-gray-950 rounded-lg p-3 max-h-52 overflow-y-auto font-mono text-xs">
      {logs.map((log, i) => {
        const colorKey = log.role.toLowerCase();
        const isError = log.message.toLowerCase().includes("fail");
        return (
          <div key={i} className="flex gap-2 leading-5">
            <span className="text-gray-500 shrink-0 select-none">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <span
              className={`font-semibold shrink-0 ${
                colorKey === "researcher"
                  ? "text-blue-400"
                  : colorKey === "writer"
                  ? "text-green-400"
                  : colorKey === "reviewer"
                  ? "text-yellow-400"
                  : colorKey === "publisher"
                  ? "text-purple-400"
                  : "text-cyan-400"
              }`}
            >
              [{log.role}]
            </span>
            <span className={isError ? "text-red-400" : "text-gray-300"}>
              {log.message}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function StepOutputCard({
  order,
  stepOut,
  colorClass,
}: {
  order: string;
  stepOut: {
    role: string;
    output: Record<string, unknown>;
    status: string;
    error?: string;
    duration_ms?: number;
  };
  colorClass: string;
}) {
  const outputText =
    typeof stepOut.output?.text === "string"
      ? stepOut.output.text
      : JSON.stringify(stepOut.output, null, 2);

  return (
    <div className={`rounded-lg border p-4 ${colorClass}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="font-semibold text-sm">{stepOut.role}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            STATUS_BADGE[stepOut.status] ?? "bg-gray-100 text-gray-600"
          }`}
        >
          {stepOut.status}
        </span>
        {stepOut.duration_ms != null && (
          <span className="text-xs opacity-60 ml-auto">
            {(stepOut.duration_ms / 1000).toFixed(2)}s
          </span>
        )}
      </div>
      {stepOut.error ? (
        <p className="text-sm text-red-700">{stepOut.error}</p>
      ) : (
        <pre className="text-sm whitespace-pre-wrap break-words opacity-90 max-h-40 overflow-y-auto">
          {outputText}
        </pre>
      )}
    </div>
  );
}

function RunHistoryPanel({
  teamId,
  agents,
  steps,
}: {
  teamId: string;
  agents: AgentDefinition[];
  steps: TeamStep[];
}) {
  const [runs, setRuns] = useState<TeamRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listTeamRuns(teamId)
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [teamId]);

  if (loading) {
    return <p className="text-xs text-gray-400 mt-2">Loading run history…</p>;
  }
  if (!runs.length) {
    return <p className="text-xs text-gray-400 mt-2">No runs yet.</p>;
  }

  return (
    <div className="mt-4 space-y-2">
      <p className="text-sm font-semibold text-gray-600">Run History</p>
      {runs.map((run) => (
        <div
          key={run.id}
          className="border border-gray-100 rounded-lg bg-gray-50 overflow-hidden"
        >
          <button
            className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-100 transition"
            onClick={() => setExpanded(expanded === run.id ? null : run.id)}
          >
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                STATUS_BADGE[run.status] ?? "bg-gray-100 text-gray-600"
              }`}
            >
              {run.status}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(run.started_at).toLocaleString()}
            </span>
            {run.duration_ms != null && (
              <span className="text-xs text-gray-400 ml-auto">
                {(run.duration_ms / 1000).toFixed(2)}s
              </span>
            )}
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ml-1 ${
                expanded === run.id ? "rotate-180" : ""
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {expanded === run.id && (
            <div className="px-4 pb-4 space-y-3">
              <WorkflowPipeline
                steps={steps}
                stepOutputs={run.step_outputs as Record<string, unknown>}
              />

              {Object.entries(run.step_outputs)
                .sort(([a], [b]) => parseInt(a) - parseInt(b))
                .map(([order, stepOut]) => {
                  const so = stepOut as {
                    role: string;
                    output: Record<string, unknown>;
                    status: string;
                    error?: string;
                    duration_ms?: number;
                  };
                  const colorIdx = parseInt(order) % STEP_COLORS.length;
                  return (
                    <StepOutputCard
                      key={order}
                      order={order}
                      stepOut={so}
                      colorClass={STEP_COLORS[colorIdx]}
                    />
                  );
                })}

              <ChatLog logs={run.logs} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<AgentTeam[]>([]);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formSteps, setFormSteps] = useState<FormStep[]>([
    { role: "", agent_id: "" },
  ]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [runResults, setRunResults] = useState<Record<string, TeamRun>>({});
  const [runningId, setRunningId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState<Record<string, boolean>>({});

  useEffect(() => {
    listTeams().then(setTeams).catch(console.error);
    listAgents().then(setAgents).catch(console.error);
  }, []);

  function resetForm() {
    setFormName("");
    setFormDesc("");
    setFormSteps([{ role: "", agent_id: "" }]);
    setFormError(null);
  }

  async function handleSave() {
    if (!formName.trim()) {
      setFormError("Name is required.");
      return;
    }
    for (const s of formSteps) {
      if (!s.role.trim() || !s.agent_id) {
        setFormError("Each step must have a role and an agent selected.");
        return;
      }
    }
    setSaving(true);
    setFormError(null);
    try {
      const steps: TeamStep[] = formSteps.map((s, i) => ({
        agent_id: s.agent_id,
        role: s.role.trim(),
        order: i,
      }));
      const team = await createTeam({
        name: formName.trim(),
        description: formDesc.trim() || undefined,
        workflow_type: "sequential",
        steps,
      });
      setTeams((prev) => [team, ...prev]);
      setShowForm(false);
      resetForm();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Failed to save team.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteTeam(id);
      setTeams((prev) => prev.filter((t) => t.id !== id));
      setRunResults((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (e) {
      console.error(e);
    }
  }

  async function handleRun(team: AgentTeam) {
    setRunningId(team.id);
    try {
      const result = await createTeamRun(team.id, {
        input: { text: "Start" },
        wait_for_completion: true,
      });
      setRunResults((prev) => ({ ...prev, [team.id]: result }));
    } catch (e) {
      console.error(e);
    } finally {
      setRunningId(null);
    }
  }

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-brand">Agent Teams</h1>
          <p className="text-sm text-gray-500 mt-1">
            Orchestrate multi-agent pipelines: researcher → writer → reviewer →
            publisher
          </p>
        </div>
        <button
          onClick={() => {
            setShowForm((v) => !v);
            if (showForm) resetForm();
          }}
          className="px-4 py-2 bg-brand text-white rounded-lg hover:opacity-90 transition font-medium"
        >
          {showForm ? "Cancel" : "New Team"}
        </button>
      </div>

      {showForm && (
        <div className="mb-8 p-6 bg-white rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">Create New Team</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Research Pipeline"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                placeholder="Optional description"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pipeline Steps (in order)
              </label>
              <p className="text-xs text-gray-400 mb-2">
                Suggested roles: Researcher, Writer, Reviewer, Publisher
              </p>
              <div className="space-y-2">
                {formSteps.map((step, idx) => (
                  <div key={idx} className="flex gap-2 items-center">
                    <span className="text-sm text-gray-400 w-6 shrink-0">
                      {idx + 1}.
                    </span>
                    <input
                      type="text"
                      value={step.role}
                      onChange={(e) =>
                        setFormSteps((prev) =>
                          prev.map((s, i) =>
                            i === idx ? { ...s, role: e.target.value } : s
                          )
                        )
                      }
                      placeholder="Role (e.g. Researcher)"
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                    />
                    <select
                      value={step.agent_id}
                      onChange={(e) =>
                        setFormSteps((prev) =>
                          prev.map((s, i) =>
                            i === idx ? { ...s, agent_id: e.target.value } : s
                          )
                        )
                      }
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
                    >
                      <option value="">Select agent...</option>
                      {agents.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                    {formSteps.length > 1 && (
                      <button
                        onClick={() =>
                          setFormSteps((prev) =>
                            prev.filter((_, i) => i !== idx)
                          )
                        }
                        className="text-red-400 hover:text-red-600 text-sm font-medium px-2"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {formSteps.length > 1 && (
                <div className="mt-3 mb-1">
                  <WorkflowPipeline steps={formSteps.map((s, i) => ({ agent_id: s.agent_id, role: s.role || `Step ${i + 1}`, order: i }))} />
                </div>
              )}
              <button
                onClick={() =>
                  setFormSteps((prev) => [
                    ...prev,
                    { role: "", agent_id: "" },
                  ])
                }
                className="mt-2 text-sm text-blue-600 hover:underline"
              >
                + Add Step
              </button>
            </div>

            {formError && (
              <p className="text-sm text-red-600">{formError}</p>
            )}

            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}

      {teams.length === 0 && !showForm && (
        <p className="text-gray-500">No teams yet. Create one to get started.</p>
      )}

      <div className="space-y-6">
        {teams.map((team) => {
          const runResult = runResults[team.id];
          const isRunning = runningId === team.id;

          return (
            <div
              key={team.id}
              className="bg-white rounded-xl shadow border border-gray-100 p-6"
            >
              <div className="flex items-start justify-between gap-4 mb-1">
                <div>
                  <h2 className="text-xl font-semibold">{team.name}</h2>
                  {team.description && (
                    <p className="text-gray-500 text-sm mt-0.5">
                      {team.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full font-medium">
                    {team.workflow_type}
                  </span>
                  <button
                    onClick={() => handleRun(team)}
                    disabled={isRunning}
                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition disabled:opacity-60"
                  >
                    {isRunning ? "Running..." : "Run"}
                  </button>
                  <button
                    onClick={() => handleDelete(team.id)}
                    className="px-3 py-1.5 bg-red-50 text-red-600 text-sm rounded-lg hover:bg-red-100 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Workflow pipeline visualization */}
              {team.steps.length > 0 && (
                <WorkflowPipeline
                  steps={team.steps}
                  stepOutputs={
                    runResult
                      ? (runResult.step_outputs as Record<string, unknown>)
                      : undefined
                  }
                  isRunning={isRunning}
                />
              )}

              {/* Live run result */}
              {runResult && (
                <div className="mt-4 border-t pt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm font-semibold text-gray-700">
                      Last Run
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        STATUS_BADGE[runResult.status] ??
                        "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {runResult.status}
                    </span>
                    {runResult.duration_ms != null && (
                      <span className="text-xs text-gray-400">
                        {(runResult.duration_ms / 1000).toFixed(2)}s
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    {Object.entries(runResult.step_outputs)
                      .sort(([a], [b]) => parseInt(a) - parseInt(b))
                      .map(([order, stepOut]) => {
                        const so = stepOut as {
                          role: string;
                          output: Record<string, unknown>;
                          status: string;
                          error?: string;
                          duration_ms?: number;
                        };
                        const colorIdx =
                          parseInt(order) % STEP_COLORS.length;
                        return (
                          <StepOutputCard
                            key={order}
                            order={order}
                            stepOut={so}
                            colorClass={STEP_COLORS[colorIdx]}
                          />
                        );
                      })}
                  </div>

                  {/* Agent chat logs */}
                  {runResult.logs.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-semibold text-gray-500 mb-1">
                        Agent Chat Log
                      </p>
                      <ChatLog logs={runResult.logs} />
                    </div>
                  )}
                </div>
              )}

              {/* Run history toggle */}
              <div className="mt-4 border-t pt-3">
                <button
                  onClick={() =>
                    setShowHistory((prev) => ({
                      ...prev,
                      [team.id]: !prev[team.id],
                    }))
                  }
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <svg
                    className={`w-3.5 h-3.5 transition-transform ${
                      showHistory[team.id] ? "rotate-180" : ""
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                  {showHistory[team.id] ? "Hide" : "Show"} run history
                </button>

                {showHistory[team.id] && (
                  <RunHistoryPanel
                    teamId={team.id}
                    agents={agents}
                    steps={team.steps}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
