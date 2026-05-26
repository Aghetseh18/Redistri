"use client";
import type { ClusterEvent } from "@/types";
import { Trash2 } from "lucide-react";

const eventColor: Record<string, string> = {
  connected:          "text-blue-400",
  heartbeat:          "text-gray-600",
  master_elected:     "text-yellow-400",
  failover_forced:    "text-orange-400",
  node_joined:        "text-green-400",
  node_removed:       "text-red-400",
  node_failed:        "text-red-500",
  node_rejoined:      "text-teal-400",
  entities_rebalanced:"text-purple-400",
};

function ts(unix: number) {
  return new Date(unix * 1000).toLocaleTimeString();
}

interface Props {
  events: ClusterEvent[];
  onClear: () => void;
}

export default function EventLog({ events, onClear }: Props) {
  const visible = events.filter((e) => e.event !== "heartbeat");

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Live Event Log
        </p>
        <button onClick={onClear} className="text-gray-600 hover:text-gray-400 transition-colors">
          <Trash2 size={13} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto space-y-1 font-mono text-[11px]">
        {visible.length === 0 && (
          <p className="text-gray-700 italic">Waiting for cluster events…</p>
        )}
        {visible.map((ev, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-gray-700 shrink-0">{ts(ev.timestamp)}</span>
            <span className={`font-semibold shrink-0 ${eventColor[ev.event] ?? "text-gray-400"}`}>
              {ev.event}
            </span>
            <span className="text-gray-500 truncate">
              {Object.entries(ev.data ?? {})
                .filter(([k]) => k !== "nodes" && k !== "metrics")
                .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                .join(" ")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
