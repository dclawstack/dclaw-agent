"use client";

const nodeKinds = [
  { type: "input", label: "Input", color: "border-blue-500" },
  { type: "llm", label: "LLM", color: "border-purple-500" },
  { type: "tool", label: "Tool", color: "border-orange-500" },
  { type: "memory", label: "Memory", color: "border-pink-500" },
  { type: "condition", label: "Condition", color: "border-yellow-500" },
  { type: "output", label: "Output", color: "border-green-500" },
];

export default function NodePalette() {
  function onDragStart(event: React.DragEvent, nodeType: string) {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  }

  return (
    <div className="w-48 bg-white border-r border-gray-200 p-4 flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Palette
      </h3>
      {nodeKinds.map((kind) => (
        <div
          key={kind.type}
          className={`p-3 rounded-lg border-2 ${kind.color} bg-white cursor-grab hover:shadow transition`}
          draggable
          onDragStart={(e) => onDragStart(e, kind.type)}
        >
          <span className="text-sm font-medium">{kind.label}</span>
        </div>
      ))}
    </div>
  );
}
