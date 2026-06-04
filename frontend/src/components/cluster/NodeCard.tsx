"use client";
import type { NodeInfo } from "@/types";
import { Crown, Shield, Cpu, MemoryStick, Zap, Clock } from "lucide-react";
import clsx from "clsx";

const statusColor: Record<string, string> = {
  healthy: "bg-green-500/15 text-green-400 border-green-500/30",
  degraded: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  joining: "bg-blue-500/15 text-blue-400 border-blue-500/30",
};
const statusDot: Record<string, string> = {
  healthy: "bg-green-400",
  degraded: "bg-yellow-400",
  failed: "bg-red-400",
  joining: "bg-blue-400",
};

function fmt(s?: number) {
  if (!s) return "0s";
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

interface Props {
  node: NodeInfo;
  masterIp?: string;
  onFailover?: (id: string) => void;
  onRemove?: (id: string) => void;
}

export default function NodeCard({ node, masterIp, onFailover, onRemove }: Props) {
  const isMaster = node.role === "master";
  const m = node.metrics ?? {};

  return (
    <div className={clsx(
      "rounded-xl border p-4 flex flex-col gap-3 transition-all",
      node.status === "failed"
        ? "border-red-500/40 bg-red-950/10"
        : isMaster
          ? "border-blue-500/40 bg-blue-950/10"
          : "border-gray-700 bg-gray-900"
    )}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {isMaster
            ? <Crown size={15} className="text-yellow-400 shrink-0" />
            : <Shield size={15} className="text-purple-400 shrink-0" />
          }
          <div className="min-w-0">
            <p className="font-mono text-sm font-semibold text-white truncate">{node.host}:{node.port}</p>
            {node.replica_of && node.master && (
              <p className="text-[10px] text-gray-500 truncate">replica of  {node.master.host}:{node.master.port}</p>
            )}
          </div>
        </div>
        {/* Status badge */}
        <span className={clsx("shrink-0 flex items-center gap-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border", statusColor[node.status])}>
          <span className={clsx("w-1.5 h-1.5 rounded-full", statusDot[node.status])} />
          {node.status}
        </span>
      </div>

      {/* Role + Priority */}
      <div className="flex gap-2">
        <span className={clsx(
          "text-[11px] font-semibold px-2 py-0.5 rounded",
          isMaster ? "bg-yellow-500/20 text-yellow-300" : "bg-purple-500/20 text-purple-300"
        )}>
          {isMaster ? "MASTER" : "REPLICA"}
        </span>
        <span className="text-[11px] px-2 py-0.5 rounded bg-gray-800 text-gray-400">
          priority {node.priority}
        </span>
      </div>

      {/* Entities */}
      {node.entities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {node.entities.map((e) => (
            <span key={e} className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">
              {e}
            </span>
          ))}
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-gray-400 border-t border-gray-800 pt-3">
        <div className="flex items-center gap-1">
          <MemoryStick size={11} />
          {m.used_memory_human ?? "—"}
        </div>
        <div className="flex items-center gap-1">
          <Zap size={11} />
          {m.ops_per_sec ?? 0} ops/s
        </div>
        <div className="flex items-center gap-1">
          <Cpu size={11} />
          {m.connected_clients ?? 0} clients
        </div>
        <div className="flex items-center gap-1">
          <Clock size={11} />
          {fmt(m.uptime_seconds)}
        </div>
        {m.db_size !== undefined && (
          <div className="col-span-2 text-gray-500">
            {m.db_size} keys
          </div>
        )}
      </div>

      {/* Actions */}
      {node.status !== "failed" && (
        <div className="flex gap-2 border-t border-gray-800 pt-3">
          {!isMaster && onFailover && (
            <button
              onClick={() => onFailover(node.node_id)}
              className="flex-1 text-[11px] py-1 rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 font-medium transition-colors"
            >
              Promote Master
            </button>
          )}
          {onRemove && (
            <button
              onClick={() => onRemove(node.node_id)}
              className="flex-1 text-[11px] py-1 rounded bg-red-600/20 hover:bg-red-600/40 text-red-400 font-medium transition-colors"
            >
              Remove Node
            </button>
          )}
        </div>
      )}
    </div>
  );
}
