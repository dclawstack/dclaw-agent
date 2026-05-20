"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ConsolidateResponse,
  LearnPreferencesResponse,
  Memory,
  MemoryStats,
  consolidateMemories,
  createMemory,
  deleteMemory,
  getMemoryStats,
  getSessionMemories,
  learnPreferences,
  listEpisodicSessions,
  listMemories,
  retrieveMemories,
  updateMemory,
} from "@/lib/api";

type MemoryType = "episodic" | "semantic" | "preference" | "all";
type TabView = "inspector" | "sessions" | "learn";

const TYPE_BADGE: Record<string, string> = {
  episodic: "bg-blue-100 text-blue-800",
  semantic: "bg-green-100 text-green-800",
  preference: "bg-yellow-100 text-yellow-800",
};

function truncate(str: string, max: number): string {
  return str.length <= max ? str : str.slice(0, max) + "…";
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

function StatsBar({ stats }: { stats: MemoryStats | null }) {
  if (!stats) return null;
  return (
    <div className="flex flex-wrap gap-3 mb-6">
      <div className="flex items-center gap-2 bg-white border rounded-lg px-4 py-2 shadow-sm">
        <span className="text-xs text-gray-500">Total</span>
        <span className="font-semibold text-gray-900">{stats.total}</span>
      </div>
      {(["episodic", "semantic", "preference"] as const).map((t) => (
        <div
          key={t}
          className={`flex items-center gap-2 border rounded-lg px-4 py-2 shadow-sm ${TYPE_BADGE[t]}`}
        >
          <span className="text-xs capitalize">{t}</span>
          <span className="font-semibold">{stats.by_type[t] ?? 0}</span>
        </div>
      ))}
      <div className="flex items-center gap-2 bg-white border rounded-lg px-4 py-2 shadow-sm">
        <span className="text-xs text-gray-500">Avg importance</span>
        <span className="font-semibold text-gray-900">
          {stats.avg_importance.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sessions tab
// ---------------------------------------------------------------------------

function SessionsTab({ scope }: { scope: string }) {
  const [sessions, setSessions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [sessionMems, setSessionMems] = useState<Memory[]>([]);
  const [loadingMems, setLoadingMems] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listEpisodicSessions(scope)
      .then(setSessions)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [scope]);

  async function selectSession(sid: string) {
    setSelected(sid);
    setLoadingMems(true);
    setError(null);
    try {
      const mems = await getSessionMemories(sid, scope);
      setSessionMems(mems);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingMems(false);
    }
  }

  if (loading) return <div className="text-gray-500 text-sm">Loading sessions…</div>;

  if (sessions.length === 0)
    return (
      <div className="text-gray-500 text-sm">
        No episodic sessions found. Store episodic memories with a{" "}
        <code className="bg-gray-100 px-1 rounded">session_id</code> in metadata
        to see them here.
      </div>
    );

  return (
    <div className="flex gap-6">
      <div className="w-56 shrink-0">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
          Sessions
        </h3>
        <ul className="space-y-1">
          {sessions.map((sid) => (
            <li key={sid}>
              <button
                onClick={() => selectSession(sid)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition ${
                  selected === sid
                    ? "bg-blue-600 text-white"
                    : "bg-white border hover:bg-gray-50 text-gray-700"
                }`}
              >
                {sid}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="flex-1 min-w-0">
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}
        {!selected ? (
          <div className="text-gray-400 text-sm">Select a session to replay.</div>
        ) : loadingMems ? (
          <div className="text-gray-500 text-sm">Loading…</div>
        ) : sessionMems.length === 0 ? (
          <div className="text-gray-400 text-sm">No memories in this session.</div>
        ) : (
          <ol className="relative border-l border-blue-200 space-y-4 pl-4">
            {sessionMems.map((mem, i) => (
              <li key={mem.id} className="relative">
                <span className="absolute -left-[1.35rem] top-1.5 w-4 h-4 rounded-full bg-blue-500 text-white text-[10px] flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div className="bg-white border rounded-lg p-3 shadow-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs text-gray-500">{mem.key}</span>
                    <span className="text-xs text-gray-400">
                      {new Date(mem.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-800">{mem.content}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Learn Preferences tab
// ---------------------------------------------------------------------------

function LearnTab({ scope }: { scope: string }) {
  const [text, setText] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LearnPreferencesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [consolidating, setConsolidating] = useState(false);
  const [consolidateResult, setConsolidateResult] =
    useState<ConsolidateResponse | null>(null);
  const [maxToKeep, setMaxToKeep] = useState(100);

  async function handleLearn() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await learnPreferences({
        scope,
        text,
        session_id: sessionId.trim() || undefined,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleConsolidate() {
    setConsolidating(true);
    setError(null);
    setConsolidateResult(null);
    try {
      const res = await consolidateMemories({
        scope,
        max_to_keep: maxToKeep,
      });
      setConsolidateResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setConsolidating(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Preference Learning */}
      <div className="bg-white border rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold mb-1">Learn User Preferences</h3>
        <p className="text-sm text-gray-500 mb-4">
          Paste any text (chat history, notes, instructions). Preference signals
          like "I prefer X" or "I always use Y" are auto-extracted and stored.
        </p>
        <div className="space-y-3">
          <textarea
            rows={5}
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder='e.g. "I prefer dark mode. I always use TypeScript. I like concise responses."'
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex gap-3 items-center">
            <input
              className="border rounded-lg px-3 py-1.5 text-sm w-48"
              placeholder="Session ID (optional)"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
            />
            <button
              onClick={handleLearn}
              disabled={loading || !text.trim()}
              className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {loading ? "Learning…" : "Extract & Store Preferences"}
            </button>
          </div>
        </div>
        {error && (
          <div className="mt-3 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}
        {result && (
          <div className="mt-4">
            {result.count === 0 ? (
              <p className="text-sm text-gray-500">
                No new preference signals found in the text.
              </p>
            ) : (
              <>
                <p className="text-sm font-medium text-green-700 mb-2">
                  Stored {result.count} new preference{result.count !== 1 ? "s" : ""}:
                </p>
                <ul className="space-y-1">
                  {result.learned.map((m) => (
                    <li
                      key={m.id}
                      className="text-sm text-gray-800 bg-yellow-50 border border-yellow-200 rounded px-3 py-1"
                    >
                      {m.content}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>

      {/* Memory Consolidation */}
      <div className="bg-white border rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold mb-1">Consolidate Memories</h3>
        <p className="text-sm text-gray-500 mb-4">
          Prune low-importance, rarely-accessed memories when the store grows
          too large. Memories are removed oldest-and-least-important first.
        </p>
        <div className="flex gap-3 items-center">
          <label className="text-sm text-gray-700">Keep at most</label>
          <input
            type="number"
            min={1}
            className="border rounded-lg px-3 py-1.5 text-sm w-24"
            value={maxToKeep}
            onChange={(e) => setMaxToKeep(parseInt(e.target.value, 10) || 100)}
          />
          <label className="text-sm text-gray-700">memories</label>
          <button
            onClick={handleConsolidate}
            disabled={consolidating}
            className="px-4 py-1.5 bg-orange-600 text-white rounded-lg text-sm hover:bg-orange-700 disabled:opacity-50 transition"
          >
            {consolidating ? "Consolidating…" : "Consolidate"}
          </button>
        </div>
        {consolidateResult && (
          <p className="mt-3 text-sm text-gray-700">
            Deleted{" "}
            <span className="font-semibold text-red-600">
              {consolidateResult.deleted}
            </span>{" "}
            memories.{" "}
            <span className="font-semibold">{consolidateResult.remaining}</span>{" "}
            remaining.
          </p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function MemoryInspectorPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [filterType, setFilterType] = useState<MemoryType>("all");
  const [scopeInput, setScopeInput] = useState("global");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabView>("inspector");

  // Add form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [addScope, setAddScope] = useState("global");
  const [addType, setAddType] = useState<"episodic" | "semantic" | "preference">(
    "episodic"
  );
  const [addKey, setAddKey] = useState("");
  const [addContent, setAddContent] = useState("");
  const [addImportance, setAddImportance] = useState(0.5);
  const [addSaving, setAddSaving] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editImportance, setEditImportance] = useState(0.5);
  const [editSaving, setEditSaving] = useState(false);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const type = filterType === "all" ? undefined : filterType;
      const [data, statsData] = await Promise.all([
        listMemories(scopeInput, type),
        getMemoryStats(scopeInput),
      ]);
      setMemories(data);
      setStats(statsData);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [filterType, scopeInput]);

  async function handleSearch() {
    if (!searchQuery.trim()) {
      await loadMemories();
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await retrieveMemories({
        scope: scopeInput,
        query: searchQuery,
        top_k: 20,
      });
      setMemories(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "inspector") loadMemories();
  }, [filterType, scopeInput, activeTab, loadMemories]);

  async function handleAddMemory() {
    if (!addKey.trim() || !addContent.trim()) return;
    setAddSaving(true);
    try {
      const mem = await createMemory({
        scope: addScope,
        memory_type: addType,
        key: addKey,
        content: addContent,
        importance: addImportance,
      });
      setMemories((prev) => [mem, ...prev]);
      setShowAddForm(false);
      setAddKey("");
      setAddContent("");
      setAddImportance(0.5);
      setAddScope("global");
      setAddType("episodic");
      // Refresh stats
      getMemoryStats(scopeInput).then(setStats).catch(() => {});
    } catch (e) {
      setError(String(e));
    } finally {
      setAddSaving(false);
    }
  }

  function startEdit(mem: Memory) {
    setEditingId(mem.id);
    setEditContent(mem.content);
    setEditImportance(mem.importance);
  }

  async function handleSaveEdit(id: string) {
    setEditSaving(true);
    try {
      const updated = await updateMemory(id, {
        content: editContent,
        importance: editImportance,
      });
      setMemories((prev) => prev.map((m) => (m.id === id ? updated : m)));
      setEditingId(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setEditSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this memory?")) return;
    try {
      await deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      getMemoryStats(scopeInput).then(setStats).catch(() => {});
    } catch (e) {
      setError(String(e));
    }
  }

  const typeButtons: { label: string; value: MemoryType }[] = [
    { label: "All", value: "all" },
    { label: "Episodic", value: "episodic" },
    { label: "Semantic", value: "semantic" },
    { label: "Preference", value: "preference" },
  ];

  const tabs: { label: string; value: TabView }[] = [
    { label: "Inspector", value: "inspector" },
    { label: "Sessions", value: "sessions" },
    { label: "Learn & Consolidate", value: "learn" },
  ];

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold">Memory Inspector</h1>
        {activeTab === "inspector" && (
          <button
            onClick={() => setShowAddForm((v) => !v)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            {showAddForm ? "Cancel" : "Add Memory"}
          </button>
        )}
      </div>

      {/* Scope selector (shared across tabs) */}
      <div className="flex items-center gap-2 mb-4">
        <label className="text-sm text-gray-600">Scope:</label>
        <input
          className="border rounded-lg px-3 py-1.5 text-sm"
          value={scopeInput}
          onChange={(e) => setScopeInput(e.target.value)}
          placeholder="global"
        />
      </div>

      {/* Stats */}
      <StatsBar stats={stats} />

      {/* Tab navigation */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-2 text-sm font-medium transition border-b-2 -mb-px ${
              activeTab === tab.value
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Inspector tab ── */}
      {activeTab === "inspector" && (
        <>
          {showAddForm && (
            <div className="mb-6 p-6 bg-white rounded-xl shadow border border-gray-100">
              <h2 className="text-lg font-semibold mb-4">New Memory</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Scope
                  </label>
                  <input
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={addScope}
                    onChange={(e) => setAddScope(e.target.value)}
                    placeholder="global or agent UUID"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type
                  </label>
                  <select
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={addType}
                    onChange={(e) =>
                      setAddType(
                        e.target.value as "episodic" | "semantic" | "preference"
                      )
                    }
                  >
                    <option value="episodic">Episodic</option>
                    <option value="semantic">Semantic</option>
                    <option value="preference">Preference</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Key
                  </label>
                  <input
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={addKey}
                    onChange={(e) => setAddKey(e.target.value)}
                    placeholder="Short identifier"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Importance (0.0 – 1.0)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={addImportance}
                    onChange={(e) =>
                      setAddImportance(parseFloat(e.target.value))
                    }
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Content
                  </label>
                  <textarea
                    rows={3}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    value={addContent}
                    onChange={(e) => setAddContent(e.target.value)}
                    placeholder="Memory content"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleAddMemory}
                  disabled={addSaving || !addKey.trim() || !addContent.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition text-sm"
                >
                  {addSaving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <div className="flex gap-1">
              {typeButtons.map((btn) => (
                <button
                  key={btn.value}
                  onClick={() => setFilterType(btn.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                    filterType === btn.value
                      ? "bg-gray-900 text-white"
                      : "bg-white border text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>
            <input
              className="border rounded-lg px-3 py-1.5 text-sm flex-1 min-w-48"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search query (BM25)…"
            />
            <button
              onClick={handleSearch}
              className="px-3 py-1.5 bg-gray-900 text-white rounded-lg text-sm hover:bg-gray-700 transition"
            >
              Search
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-gray-500 text-sm">Loading...</div>
          ) : memories.length === 0 ? (
            <div className="text-gray-500 text-sm">No memories found.</div>
          ) : (
            <div className="bg-white rounded-xl shadow border border-gray-100 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Type
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Key
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Content
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Importance
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Access Count
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Last Accessed
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {memories.map((mem) => (
                    <tr key={mem.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            TYPE_BADGE[mem.memory_type] ??
                            "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {mem.memory_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-700 max-w-[160px] truncate">
                        {mem.key}
                      </td>
                      <td className="px-4 py-3 text-gray-700 max-w-[280px]">
                        {editingId === mem.id ? (
                          <textarea
                            rows={2}
                            className="w-full border rounded px-2 py-1 text-xs"
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                          />
                        ) : (
                          truncate(mem.content, 80)
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {editingId === mem.id ? (
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.1}
                            className="w-20 border rounded px-2 py-1 text-xs"
                            value={editImportance}
                            onChange={(e) =>
                              setEditImportance(parseFloat(e.target.value))
                            }
                          />
                        ) : (
                          mem.importance.toFixed(1)
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {mem.access_count}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {mem.last_accessed_at
                          ? new Date(mem.last_accessed_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          {editingId === mem.id ? (
                            <>
                              <button
                                onClick={() => handleSaveEdit(mem.id)}
                                disabled={editSaving}
                                className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 disabled:opacity-50 transition"
                              >
                                {editSaving ? "Saving..." : "Save"}
                              </button>
                              <button
                                onClick={() => setEditingId(null)}
                                className="px-2 py-1 border rounded text-xs hover:bg-gray-50 transition"
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => startEdit(mem)}
                                className="px-2 py-1 border rounded text-xs hover:bg-gray-50 transition"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDelete(mem.id)}
                                className="px-2 py-1 bg-red-50 text-red-600 border border-red-200 rounded text-xs hover:bg-red-100 transition"
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── Sessions tab ── */}
      {activeTab === "sessions" && <SessionsTab scope={scopeInput} />}

      {/* ── Learn tab ── */}
      {activeTab === "learn" && <LearnTab scope={scopeInput} />}
    </main>
  );
}
