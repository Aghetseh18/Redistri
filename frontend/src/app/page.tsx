"use client";
import Navbar from "@/components/layout/Navbar";
import EventLog from "@/components/cluster/EventLog";
import { useClusterWebSocket } from "@/hooks/useWebSocket";
import { getMetrics } from "@/lib/api";
import { useEffect, useState } from "react";
import type { NodeInfo } from "@/types";
import { Crown, Server, AlertTriangle, CheckCircle, Database } from "lucide-react";

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color: string }) {
  return (
    <div className={`rounded-xl border p-4 bg-gray-900 ${color}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { topology, events, clearEvents, connected } = useClusterWebSocket();
  const [metrics, setMetrics] = useState<NodeInfo[]>([]);

  useEffect(() => {
    const load = () => getMetrics().then(setMetrics).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const master = topology?.nodes.find((n) => n.role === "master");

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Dashboard" subtitle="Real-time cluster overview" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Nodes"
            value={topology?.total_nodes ?? "—"}
            color="border-gray-700"
          />
          <StatCard
            label="Healthy"
            value={topology?.healthy_nodes ?? "—"}
            color="border-green-500/30"
          />
          <StatCard
            label="Failed"
            value={topology?.failed_nodes ?? "—"}
            sub={topology?.failed_nodes ? "Failover may be active" : "All OK"}
            color={topology?.failed_nodes ? "border-red-500/30" : "border-gray-700"}
          />
          <StatCard
            label="Master"
            value={master ? master.node_id : "None"}
            sub={`priority ${master?.priority ?? "—"}`}
            color="border-yellow-500/30"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Entity distribution */}
          <div className="lg:col-span-2 rounded-xl border border-gray-800 bg-gray-900 p-5">
            <div className="flex items-center gap-2 mb-4">
              <Database size={15} className="text-indigo-400" />
              <p className="text-sm font-semibold text-gray-200">Entity Distribution</p>
              <span className="text-[10px] text-gray-600 ml-auto">which machine stores what</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[11px] text-gray-600 uppercase tracking-wider border-b border-gray-800">
                  <th className="text-left pb-2">Entity Type</th>
                  <th className="text-left pb-2">Node (Machine)</th>
                  <th className="text-left pb-2">Role</th>
                  <th className="text-left pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {topology
                  ? Object.entries(topology.entity_distribution).map(([entity, nodeId]) => {
                      const node = topology.nodes.find((n) => n.node_id === nodeId);
                      return (
                        <tr key={entity} className="text-xs">
                          <td className="py-2 font-mono text-indigo-300">{entity}</td>
                          <td className="py-2 font-mono text-gray-300">{nodeId}</td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              node?.role === "master" ? "bg-yellow-500/20 text-yellow-300" : "bg-purple-500/20 text-purple-300"
                            }`}>
                              {node?.role ?? "—"}
                            </span>
                          </td>
                          <td className="py-2">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              node?.status === "healthy" ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"
                            }`}>
                              {node?.status ?? "—"}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  : <tr><td colSpan={4} className="py-6 text-center text-gray-600">Connecting to cluster…</td></tr>
                }
              </tbody>
            </table>
          </div>

          {/* Event log */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 flex flex-col" style={{ minHeight: 300 }}>
            <EventLog events={events} onClear={clearEvents} />
          </div>
        </div>

        {/* Node metrics */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Server size={15} className="text-blue-400" />
            <p className="text-sm font-semibold text-gray-200">Node Metrics</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[11px] text-gray-600 uppercase tracking-wider border-b border-gray-800">
                  {["Node","Role","Status","Entities","Memory","Ops/s","Clients","Keys","Uptime"].map((h) => (
                    <th key={h} className="text-left pb-2 pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {metrics.length === 0 && (
                  <tr><td colSpan={9} className="py-6 text-center text-gray-600">Loading metrics…</td></tr>
                )}
                {metrics.map((n) => (
                  <tr key={n.node_id} className={n.status === "failed" ? "opacity-40" : ""}>
                    <td className="py-2 pr-4 font-mono text-white">{n.node_id}</td>
                    <td className="py-2 pr-4">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        n.role === "master" ? "bg-yellow-500/20 text-yellow-300" : "bg-purple-500/20 text-purple-300"
                      }`}>{n.role}</span>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`flex items-center gap-1 ${
                        n.status === "healthy" ? "text-green-400" : n.status === "failed" ? "text-red-400" : "text-yellow-400"
                      }`}>
                        {n.status === "healthy" ? <CheckCircle size={11} /> : <AlertTriangle size={11} />}
                        {n.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-indigo-300">{(n.entities ?? []).join(", ") || "—"}</td>
                    <td className="py-2 pr-4 text-gray-300">{(n.metrics as Record<string,unknown>)?.used_memory_human as string ?? "—"}</td>
                    <td className="py-2 pr-4 text-gray-300">{(n.metrics as Record<string,unknown>)?.ops_per_sec as number ?? 0}</td>
                    <td className="py-2 pr-4 text-gray-300">{(n.metrics as Record<string,unknown>)?.connected_clients as number ?? 0}</td>
                    <td className="py-2 pr-4 text-gray-300">{(n.metrics as Record<string,unknown>)?.db_size as number ?? 0}</td>
                    <td className="py-2 text-gray-400">
                      {(n.metrics as Record<string,unknown>)?.uptime_seconds
                        ? `${Math.floor(((n.metrics as Record<string,unknown>).uptime_seconds as number) / 60)}m`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>
  );
}
