"use client";

import { useEffect, useState } from "react";
import {
  listScheduledTasks,
  listAgents,
  createScheduledTask,
  deleteScheduledTask,
  pauseScheduledTask,
  resumeScheduledTask,
  ScheduledTask,
  ScheduledRun,
  AgentDefinition,
} from "@/lib/api";

const STATUS_BADGE: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  running: "bg-blue-100 text-blue-700 animate-pulse",
  pending: "bg-yellow-100 text-yellow-700",
  skipped: "bg-gray-100 text-gray-500",
};

const STATUS_DOT: Record<string, string> = {
  completed: "bg-green-500",
  failed: "bg-red-500",
  running: "bg-blue-500 animate-pulse",
  pending: "bg-yellow-400",
  skipped: "bg-gray-300",
};

function formatDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt || !completedAt) return "";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(iso).toLocaleDateString();
}

function formatNext(iso: string | null): string {
  if (!iso) return "—";
  const diff = new Date(iso).getTime() - Date.now();
  if (diff < 0) return "overdue";
  if (diff < 60_000) return "in <1m";
  if (diff < 3_600_000) return `in ${Math.floor(diff / 60_000)}m`;
  if (diff < 86_400_000) return `in ${Math.floor(diff / 3_600_000)}h`;
  return new Date(iso).toLocaleDateString();
}

function scheduleLabel(task: ScheduledTask): string {
  if (task.schedule_type === "cron") return `cron: ${task.cron_expr}`;
  if (task.schedule_type === "interval") {
    const secs = task.interval_seconds ?? 0;
    if (secs < 60) return `every ${secs}s`;
    if (secs < 3600) return `every ${secs / 60}m`;
    return `every ${secs / 3600}h`;
  }
  return "once";
}

function RunTimeline({ runs }: { runs: ScheduledRun[] }) {
  if (!runs.length) {
    return <p className="text-xs text-gray-400 mt-2 ml-1">No runs yet.</p>;
  }
  return (
    <div className="mt-3 space-y-1 max-h-64 overflow-y-auto">
      {runs.slice(0, 20).map((run) => (
        <div
          key={run.id}
          className="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 border border-gray-100 text-xs"
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              STATUS_DOT[run.status] ?? "bg-gray-300"
            }`}
          />
          <span
            className={`px-2 py-0.5 rounded-full font-medium shrink-0 ${
              STATUS_BADGE[run.status] ?? "bg-gray-100 text-gray-600"
            }`}
          >
            {run.status}
          </span>
          {run.attempt_number > 1 && (
            <span className="text-gray-400 shrink-0">
              attempt {run.attempt_number}
            </span>
          )}
          <span className="text-gray-500 shrink-0">
            {new Date(run.scheduled_at).toLocaleString()}
          </span>
          {run.started_at && run.completed_at && (
            <span className="text-gray-400 shrink-0">
              {formatDuration(run.started_at, run.completed_at)}
            </span>
          )}
          {run.error_message && (
            <span className="text-red-500 truncate" title={run.error_message}>
              {run.error_message}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

type FormState = {
  name: string;
  description: string;
  agent_id: string;
  schedule_type: "cron" | "interval" | "once";
  cron_expr: string;
  interval_seconds: string;
  max_retries: string;
  retry_delay_seconds: string;
};

const EMPTY_FORM: FormState = {
  name: "",
  description: "",
  agent_id: "",
  schedule_type: "interval",
  cron_expr: "0 * * * *",
  interval_seconds: "3600",
  max_retries: "3",
  retry_delay_seconds: "60",
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    listScheduledTasks().then(setTasks).catch(console.error);
    listAgents().then(setAgents).catch(console.error);
  }, []);

  function resetForm() {
    setForm(EMPTY_FORM);
    setFormError(null);
  }

  async function handleSave() {
    if (!form.name.trim()) {
      setFormError("Name is required.");
      return;
    }
    if (!form.agent_id) {
      setFormError("Select an agent.");
      return;
    }
    if (form.schedule_type === "cron" && !form.cron_expr.trim()) {
      setFormError("Cron expression is required.");
      return;
    }
    if (form.schedule_type === "interval" && !form.interval_seconds) {
      setFormError("Interval (seconds) is required.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const task = await createScheduledTask({
        agent_id: form.agent_id,
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        schedule_type: form.schedule_type,
        cron_expr: form.schedule_type === "cron" ? form.cron_expr.trim() : undefined,
        interval_seconds:
          form.schedule_type === "interval" ? parseInt(form.interval_seconds) : undefined,
        max_retries: parseInt(form.max_retries),
        retry_delay_seconds: parseInt(form.retry_delay_seconds),
      });
      setTasks((prev) => [task, ...prev]);
      setShowForm(false);
      resetForm();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Failed to create task.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteScheduledTask(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleToggle(task: ScheduledTask) {
    try {
      const updated = task.is_active
        ? await pauseScheduledTask(task.id)
        : await resumeScheduledTask(task.id);
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
    } catch (e) {
      console.error(e);
    }
  }

  const agentName = (id: string) =>
    agents.find((a) => a.id === id)?.name ?? id.slice(0, 8) + "…";

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-brand">Scheduled Tasks</h1>
          <p className="text-sm text-gray-500 mt-1">
            Agents that run on a schedule, retry on failure, and log every execution.
          </p>
        </div>
        <button
          onClick={() => {
            setShowForm((v) => !v);
            if (showForm) resetForm();
          }}
          className="px-4 py-2 bg-brand text-white rounded-lg hover:opacity-90 transition font-medium"
        >
          {showForm ? "Cancel" : "New Task"}
        </button>
      </div>

      {showForm && (
        <div className="mb-8 p-6 bg-white rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">Create Scheduled Task</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Daily Report"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Agent</label>
                <select
                  value={form.agent_id}
                  onChange={(e) => setForm((f) => ({ ...f, agent_id: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="">Select agent…</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="Optional description"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule Type
              </label>
              <div className="flex gap-3">
                {(["interval", "cron", "once"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setForm((f) => ({ ...f, schedule_type: t }))}
                    className={`px-4 py-2 rounded-lg text-sm font-medium border transition ${
                      form.schedule_type === t
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                    }`}
                  >
                    {t === "interval" ? "Interval" : t === "cron" ? "Cron" : "Run Once"}
                  </button>
                ))}
              </div>
            </div>

            {form.schedule_type === "interval" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Interval (seconds)
                </label>
                <input
                  type="number"
                  min={10}
                  value={form.interval_seconds}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, interval_seconds: e.target.value }))
                  }
                  className="w-40 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <span className="text-xs text-gray-400 ml-2">
                  {parseInt(form.interval_seconds || "0") >= 3600
                    ? `${parseInt(form.interval_seconds) / 3600}h`
                    : parseInt(form.interval_seconds || "0") >= 60
                    ? `${Math.round(parseInt(form.interval_seconds) / 60)}m`
                    : ""}
                </span>
              </div>
            )}

            {form.schedule_type === "cron" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cron Expression{" "}
                  <span className="font-normal text-gray-400">(min hour dom month dow)</span>
                </label>
                <input
                  type="text"
                  value={form.cron_expr}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, cron_expr: e.target.value }))
                  }
                  placeholder="0 9 * * 1-5"
                  className="w-64 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Examples: <code>0 9 * * 1-5</code> (weekdays 9am) · <code>*/30 * * * *</code> (every 30min)
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Retries
                </label>
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={form.max_retries}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, max_retries: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Retry Delay (seconds)
                </label>
                <input
                  type="number"
                  min={10}
                  value={form.retry_delay_seconds}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, retry_delay_seconds: e.target.value }))
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </div>

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-60"
            >
              {saving ? "Saving…" : "Create Task"}
            </button>
          </div>
        </div>
      )}

      {tasks.length === 0 && !showForm && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-1">No scheduled tasks yet.</p>
          <p className="text-sm">Create one to run agents autonomously.</p>
        </div>
      )}

      <div className="space-y-4">
        {tasks.map((task) => {
          const isOpen = expanded === task.id;
          const lastRun = task.scheduled_runs[0] ?? null;

          return (
            <div
              key={task.id}
              className="bg-white rounded-xl shadow border border-gray-100"
            >
              <div className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-lg font-semibold truncate">{task.name}</h2>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                          task.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {task.is_active ? "active" : "paused"}
                      </span>
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-mono shrink-0">
                        {scheduleLabel(task)}
                      </span>
                    </div>
                    {task.description && (
                      <p className="text-sm text-gray-500 mt-0.5">{task.description}</p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-400 flex-wrap">
                      <span>
                        Agent:{" "}
                        <span className="text-gray-600 font-medium">
                          {agentName(task.agent_id)}
                        </span>
                      </span>
                      <span>
                        Last run:{" "}
                        <span className="text-gray-600">{formatRelative(task.last_run_at)}</span>
                      </span>
                      <span>
                        Next run:{" "}
                        <span
                          className={
                            task.is_active ? "text-blue-600 font-medium" : "text-gray-400"
                          }
                        >
                          {task.is_active ? formatNext(task.next_run_at) : "—"}
                        </span>
                      </span>
                      {lastRun && (
                        <span className="flex items-center gap-1">
                          Last result:
                          <span
                            className={`ml-1 px-2 py-0.5 rounded-full font-medium ${
                              STATUS_BADGE[lastRun.status] ?? "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {lastRun.status}
                          </span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleToggle(task)}
                      className={`px-3 py-1.5 text-sm rounded-lg font-medium transition ${
                        task.is_active
                          ? "bg-yellow-50 text-yellow-700 hover:bg-yellow-100"
                          : "bg-green-50 text-green-700 hover:bg-green-100"
                      }`}
                    >
                      {task.is_active ? "Pause" : "Resume"}
                    </button>
                    <button
                      onClick={() => handleDelete(task.id)}
                      className="px-3 py-1.5 bg-red-50 text-red-600 text-sm rounded-lg hover:bg-red-100 transition"
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => setExpanded(isOpen ? null : task.id)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 transition"
                      title={isOpen ? "Collapse history" : "Expand history"}
                    >
                      <svg
                        className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
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
                  </div>
                </div>
              </div>

              {isOpen && (
                <div className="border-t border-gray-100 px-5 pb-5 pt-3">
                  <p className="text-sm font-semibold text-gray-600 mb-2">
                    Execution History
                  </p>
                  <RunTimeline runs={task.scheduled_runs} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </main>
  );
}
