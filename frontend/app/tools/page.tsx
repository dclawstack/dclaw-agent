"use client";

import { useEffect, useState } from "react";
import { listTools, installTool, uninstallTool, executeTool, Tool } from "@/lib/api";

const CATEGORY_COLORS: Record<string, string> = {
  search: "bg-blue-100 text-blue-800",
  compute: "bg-purple-100 text-purple-800",
  integration: "bg-green-100 text-green-800",
  io: "bg-yellow-100 text-yellow-800",
  code: "bg-red-100 text-red-800",
};

function categoryBadgeClass(category: string): string {
  return CATEGORY_COLORS[category] ?? "bg-gray-100 text-gray-800";
}

type TryItState = {
  values: Record<string, string>;
  result: Record<string, unknown> | null;
  loading: boolean;
  error: string | null;
};

function ToolCard({ tool, onToggleInstall }: { tool: Tool; onToggleInstall: (slug: string, install: boolean) => Promise<void> }) {
  const [tryItOpen, setTryItOpen] = useState(false);
  const [tryIt, setTryIt] = useState<TryItState>({
    values: {},
    result: null,
    loading: false,
    error: null,
  });
  const [installingState, setInstallingState] = useState(false);

  const schemaKeys = Object.keys(tool.config_schema);

  async function handleInstallToggle() {
    setInstallingState(true);
    try {
      await onToggleInstall(tool.slug, !tool.is_installed);
    } finally {
      setInstallingState(false);
    }
  }

  async function handleExecute() {
    setTryIt((prev) => ({ ...prev, loading: true, result: null, error: null }));
    try {
      const inputs: Record<string, unknown> = {};
      for (const key of schemaKeys) {
        inputs[key] = tryIt.values[key] ?? "";
      }
      const result = await executeTool(tool.slug, inputs);
      setTryIt((prev) => ({ ...prev, result, loading: false }));
    } catch (err) {
      setTryIt((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm flex flex-col">
      <div className="p-5 flex-1">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h2 className="text-lg font-semibold">{tool.name}</h2>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${categoryBadgeClass(tool.category)}`}
          >
            {tool.category}
          </span>
        </div>
        {tool.description && (
          <p className="text-sm text-gray-500 mb-3">{tool.description}</p>
        )}
        {schemaKeys.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
              Inputs
            </p>
            <table className="w-full text-xs text-left">
              <tbody>
                {schemaKeys.map((key) => (
                  <tr key={key} className="border-t border-gray-50">
                    <td className="py-1 pr-2 font-mono font-medium text-gray-700 w-1/3">
                      {key}
                    </td>
                    <td className="py-1 text-gray-500">
                      {tool.config_schema[key]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="px-5 pb-3 flex gap-2">
        <button
          onClick={handleInstallToggle}
          disabled={installingState}
          className={`flex-1 px-3 py-1.5 text-sm rounded transition ${
            tool.is_installed
              ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
              : "bg-brand text-white hover:opacity-90"
          } disabled:opacity-50`}
        >
          {installingState
            ? "..."
            : tool.is_installed
            ? "Uninstall"
            : "Install"}
        </button>
        <button
          onClick={() => setTryItOpen((o) => !o)}
          className="px-3 py-1.5 text-sm rounded border border-gray-200 hover:bg-gray-50 transition"
        >
          {tryItOpen ? "Close" : "Try It"}
        </button>
      </div>

      {tryItOpen && (
        <div className="border-t border-gray-100 px-5 py-4 bg-gray-50 rounded-b-xl">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Try It
          </p>
          <div className="flex flex-col gap-2 mb-3">
            {schemaKeys.map((key) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 mb-0.5">
                  {key}
                </label>
                <input
                  type="text"
                  value={tryIt.values[key] ?? ""}
                  onChange={(e) =>
                    setTryIt((prev) => ({
                      ...prev,
                      values: { ...prev.values, [key]: e.target.value },
                    }))
                  }
                  className="w-full px-2 py-1 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-brand"
                  placeholder={tool.config_schema[key]}
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleExecute}
            disabled={tryIt.loading}
            className="w-full px-3 py-1.5 text-sm bg-brand text-white rounded hover:opacity-90 transition disabled:opacity-50"
          >
            {tryIt.loading ? "Running..." : "Execute"}
          </button>
          {tryIt.error && (
            <p className="mt-2 text-xs text-red-600">{tryIt.error}</p>
          )}
          {tryIt.result !== null && (
            <pre className="mt-3 p-2 text-xs bg-white border border-gray-200 rounded overflow-auto max-h-48 whitespace-pre-wrap">
              {JSON.stringify(tryIt.result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTools()
      .then(setTools)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleToggleInstall(slug: string, install: boolean) {
    if (install) {
      const updated = await installTool(slug);
      setTools((prev) => prev.map((t) => (t.slug === slug ? updated : t)));
    } else {
      await uninstallTool(slug);
      setTools((prev) =>
        prev.map((t) => (t.slug === slug ? { ...t, is_installed: false } : t))
      );
    }
  }

  return (
    <main className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Tool Marketplace</h1>
      <p className="text-gray-500 mb-6">
        Browse, install, and try built-in tools for your agents.
      </p>
      {loading ? (
        <p>Loading...</p>
      ) : error ? (
        <p className="text-red-500">{error}</p>
      ) : tools.length === 0 ? (
        <p className="text-gray-500">No tools available.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tools.map((tool) => (
            <ToolCard
              key={tool.slug}
              tool={tool}
              onToggleInstall={handleToggleInstall}
            />
          ))}
        </div>
      )}
    </main>
  );
}
