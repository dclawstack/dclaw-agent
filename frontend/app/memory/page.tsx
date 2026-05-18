"use client";

import { useEffect, useState } from "react";
import {
  Memory,
  createMemory,
  deleteMemory,
  listMemories,
  retrieveMemories,
  updateMemory,
} from "@/lib/api";

type MemoryType = "episodic" | "semantic" | "preference" | "all";

const TYPE_BADGE: Record<string, string> = {
  episodic: "bg-blue-100 text-blue-800",
  semantic: "bg-green-100 text-green-800",
  preference: "bg-yellow-100 text-yellow-800",
};

function truncate(str: string, max: number): string {
  return str.length <= max ? str : str.slice(0, max) + "…";
}

export default function MemoryInspectorPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [filterType, setFilterType] = useState<MemoryType>("all");
  const [scopeInput, setScopeInput] = useState("global");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [addScope, setAddScope] = useState("global");
  const [addType, setAddType] = useState<"episodic" | "semantic" | "preference">("episodic");
  const [addKey, setAddKey] = useState("");
  const [addContent, setAddContent] = useState("");
  const [addImportance, setAddImportance] = useState(0.5);
  const [addSaving, setAddSaving] = useState(false);

  // Edit state: row id -> draft values
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editImportance, setEditImportance] = useState(0.5);
  const [editSaving, setEditSaving] = useState(false);

  async function loadMemories() {
    setLoading(true);
    setError(null);
    try {
      const type = filterType === "all" ? undefined : filterType;
      const data = await listMemories(scopeInput, type);
      setMemories(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

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
    loadMemories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType, scopeInput]);

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

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Memory Inspector</h1>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          {showAddForm ? "Cancel" : "Add Memory"}
        </button>
      </div>

      {showAddForm && (
        <div className="mb-6 p-6 bg-white rounded-xl shadow border border-gray-100">
          <h2 className="text-lg font-semibold mb-4">New Memory</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={addScope}
                onChange={(e) => setAddScope(e.target.value)}
                placeholder="global or agent UUID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={addType}
                onChange={(e) => setAddType(e.target.value as "episodic" | "semantic" | "preference")}
              >
                <option value="episodic">Episodic</option>
                <option value="semantic">Semantic</option>
                <option value="preference">Preference</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Key</label>
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
                onChange={(e) => setAddImportance(parseFloat(e.target.value))}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
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
          className="border rounded-lg px-3 py-1.5 text-sm"
          value={scopeInput}
          onChange={(e) => setScopeInput(e.target.value)}
          placeholder="Scope (e.g. global)"
        />
        <input
          className="border rounded-lg px-3 py-1.5 text-sm flex-1 min-w-48"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search query..."
        />
        <button
          onClick={handleSearch}
          className="px-3 py-1.5 bg-gray-900 text-white rounded-lg text-sm hover:bg-gray-700 transition"
        >
          Search
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Key</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Content</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Importance</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Access Count</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Last Accessed</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {memories.map((mem) => (
                <tr key={mem.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        TYPE_BADGE[mem.memory_type] ?? "bg-gray-100 text-gray-700"
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
                        onChange={(e) => setEditImportance(parseFloat(e.target.value))}
                      />
                    ) : (
                      mem.importance.toFixed(1)
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{mem.access_count}</td>
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
    </main>
  );
}
