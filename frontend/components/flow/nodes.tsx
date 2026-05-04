"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";

const typeColors: Record<string, string> = {
  input: "border-blue-500 bg-blue-50",
  llm: "border-purple-500 bg-purple-50",
  tool: "border-orange-500 bg-orange-50",
  memory: "border-pink-500 bg-pink-50",
  condition: "border-yellow-500 bg-yellow-50",
  loop: "border-indigo-500 bg-indigo-50",
  output: "border-green-500 bg-green-50",
};

export function AgentNodeComponent(props: NodeProps) {
  const { data, type } = props;
  const color = typeColors[(type as string) || "input"] || typeColors.input;
  return (
    <div className={`px-4 py-2 rounded-lg border-2 shadow-sm min-w-[120px] ${color}`}>
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
        {String(type)}
      </div>
      <div className="text-sm font-medium">{String(data?.label || "Node")}</div>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2" />
    </div>
  );
}

export const nodeTypes = {
  input: AgentNodeComponent,
  llm: AgentNodeComponent,
  tool: AgentNodeComponent,
  memory: AgentNodeComponent,
  condition: AgentNodeComponent,
  loop: AgentNodeComponent,
  output: AgentNodeComponent,
};
