"use client";

import { useEffect, useState } from "react";
import {
  listTeams,
  listAgents,
  createTeam,
  deleteTeam,
  createTeamRun,
  AgentTeam,
  AgentDefinition,
  TeamStep,
  TeamRun,
} from "@/lib/api";

const STEP_COLORS = [
  "bg-blue-100 border-blue-400 text-blue-800",
  "bg-green-100 border-green-400 text-green-800",
  "bg-yellow-100 border-yellow-400 text-yellow-800",
  "bg-red-100 border-red-400 text-red-800",
];

const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700",
  pending: "bg-gray-100 text-gray-600",
};

type FormStep = { role: string; agent_id: string };

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

  // run results keyed by team id
  const [runResults, setRunResults] = useState<Record<string, TeamRun>>({});
  const [runningId, setRunningId] = useState<string | null>(null);

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
        <h1 className="text-3xl font-bold text-brand">Agent Teams</h1>
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
                Steps (in order)
              </label>
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
              <div className="flex items-start justify-between gap-4 mb-3">
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

              {team.steps.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {[...team.steps]
                    .sort((a, b) => a.order - b.order)
                    .map((step, idx) => (
                      <span
                        key={idx}
                        className={`text-xs px-2 py-1 rounded-full border font-medium ${
                          STEP_COLORS[idx % STEP_COLORS.length]
                        }`}
                      >
                        {step.order + 1}. {step.role}
                      </span>
                    ))}
                </div>
              )}

              {runResult && (
                <div className="mt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm font-semibold text-gray-700">
                      Last Run
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        STATUS_BADGE[runResult.status] ?? "bg-gray-100 text-gray-600"
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
                        };
                        const colorIdx =
                          parseInt(order) % STEP_COLORS.length;
                        const color = STEP_COLORS[colorIdx];
                        const outputText =
                          typeof so.output?.text === "string"
                            ? so.output.text
                            : JSON.stringify(so.output, null, 2);

                        return (
                          <div
                            key={order}
                            className={`rounded-lg border p-4 ${color}`}
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <span className="font-semibold text-sm">
                                {so.role}
                              </span>
                              <span
                                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                  STATUS_BADGE[so.status] ??
                                  "bg-gray-100 text-gray-600"
                                }`}
                              >
                                {so.status}
                              </span>
                            </div>
                            {so.error ? (
                              <p className="text-sm text-red-700">{so.error}</p>
                            ) : (
                              <pre className="text-sm whitespace-pre-wrap break-words opacity-90">
                                {outputText}
                              </pre>
                            )}
                          </div>
                        );
                      })}
                  </div>

                  {runResult.logs.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        Show execution log ({runResult.logs.length} entries)
                      </summary>
                      <div className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                        {runResult.logs.map((log, i) => (
                          <div
                            key={i}
                            className="text-xs text-gray-600 font-mono flex gap-2"
                          >
                            <span className="text-gray-400 shrink-0">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="font-medium shrink-0">
                              [{log.role}]
                            </span>
                            <span>{log.message}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}
