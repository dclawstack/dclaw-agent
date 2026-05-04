"use client";

import { useEffect, useState } from "react";
import type { Node } from "@xyflow/react";

export default function PropertyPanel({
  selected,
  onChange,
}: {
  selected: Node | null;
  onChange: (node: Node) => void;
}) {
  const [config, setConfig] = useState<string>("{}");

  useEffect(() => {
    if (selected) {
      setConfig(JSON.stringify(selected.data?.config || {}, null, 2));
    }
  }, [selected?.id]);

  if (!selected) {
    return (
      <div className="w-64 bg-white border-l border-gray-200 p-4">
        <p className="text-sm text-gray-400">Select a node to edit properties.</p>
      </div>
    );
  }

  function save() {
    if (!selected) return;
    try {
      const parsed = JSON.parse(config);
      onChange({
        id: selected.id,
        type: selected.type,
        position: selected.position,
        data: { ...selected.data, config: parsed },
      } as Node);
    } catch {
      alert("Invalid JSON");
    }
  }

  return (
    <div className="w-64 bg-white border-l border-gray-200 p-4 flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Properties
      </h3>
      <div>
        <label className="text-xs text-gray-500">Label</label>
        <input
          className="w-full mt-1 px-2 py-1 border rounded text-sm"
          value={String(selected.data?.label || "")}
          onChange={(e) =>
            onChange({
              ...selected,
              data: { ...selected.data, label: e.target.value },
            })
          }
        />
      </div>
      <div>
        <label className="text-xs text-gray-500">Config (JSON)</label>
        <textarea
          className="w-full mt-1 px-2 py-1 border rounded text-sm font-mono"
          rows={10}
          value={config}
          onChange={(e) => setConfig(e.target.value)}
        />
      </div>
      <button
        onClick={save}
        className="px-3 py-1.5 text-sm bg-brand text-white rounded hover:opacity-90"
      >
        Save
      </button>
    </div>
  );
}
