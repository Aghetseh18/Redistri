"use client";
import { useEffect, useState, useCallback } from "react";
import Navbar from "@/components/layout/Navbar";
import NodeCard from "@/components/cluster/NodeCard";
import EventLog from "@/components/cluster/EventLog";
import { useClusterWebSocket } from "@/hooks/useWebSocket";
import {
  forceFailover, removeNode, rebalance, registerNode,
} from "@/lib/api";
import type { NodeInfo } from "@/types";
import { RefreshCw, PlusCircle, RotateCcw } from "lucide-react";

function Toast({ msg, ok }: { msg: string; ok: boolean }) {
  return (
    <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-sm font-medium ${ok ? "bg-green-600 text-white" : "bg-red-600 text-white"
      }`}>{msg}</div>
  );
}

export default function ClusterPage() {
  const { topology, events, clearEvents } = useClusterWebSocket();
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ host: "", port: "6379", priority: "" });
  const [loading, setLoading] = useState<string | null>(null);

  function notify(msg: string, ok = true) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  console.log(topology)

  async function handleFailover(id: string) {
    setLoading(id);
    try {
      await forceFailover(id);
      notify(`Failover triggered → ${id} is now master`);
    } catch (e) {
      notify((e as Error).message, false);
    } finally {
      setLoading(null);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm(`Remove node ${id} from the cluster?`)) return;
    setLoading(id);
    try {
      await removeNode(id);
      notify(`Node ${id} removed`);
    } catch (e) {
      notify((e as Error).message, false);
    } finally {
      setLoading(null);
    }
  }

  async function handleRebalance() {
    setLoading("rebalance");
    try {
      await rebalance();
      notify("Entity types rebalanced across nodes");
    } catch (e) {
      notify((e as Error).message, false);
    } finally {
      setLoading(null);
    }
  }

  async function handleAddNode(e: React.FormEvent) {
    e.preventDefault();
    setLoading("add");
    try {
      await registerNode(
        addForm.host,
        parseInt(addForm.port),
        addForm.priority ? parseInt(addForm.priority) : undefined,
      );
      notify(`Node ${addForm.host}:${addForm.port} registered`);
      setShowAdd(false);
      setAddForm({ host: "", port: "6379", priority: "" });
    } catch (err) {
      notify((err as Error).message, false);
    } finally {
      setLoading(null);
    }
  }

  const nodes = topology?.nodes ?? [];
  const masters = nodes.filter((n) => n.role === "master");
  const replicas = nodes.filter((n) => n.role === "replica");
  masters.forEach(n => {
    n.repl = replicas.filter(r => r.replica_of == n.node_id)
  });

  replicas.forEach(r => {
    r.master = masters.find(m => r.replica_of == m.node_id)
  });
  console.log('masters ', masters)
  console.log('replicas', replicas)


  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Cluster Management" subtitle="Nodes · failover · rebalancing" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Toolbar */}
        <div className="flex flex-wrap gap-3 items-center">
          <button
            onClick={handleRebalance}
            disabled={loading === "rebalance"}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            <RotateCcw size={14} className={loading === "rebalance" ? "animate-spin" : ""} />
            Rebalance Entities
          </button>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-700 hover:bg-green-600 text-white text-sm font-medium transition-colors"
          >
            <PlusCircle size={14} />
            Add Node
          </button>
          <div className="ml-auto text-xs text-gray-500">
            {nodes.length} nodes · {masters.length} masters · {replicas.length} replicas
          </div>
        </div>

        {/* Add node form */}
        {showAdd && (
          <form onSubmit={handleAddNode} className="rounded-xl border border-gray-700 bg-gray-900 p-5 flex flex-wrap gap-4 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Host / IP</label>
              <input
                required value={addForm.host}
                onChange={(e) => setAddForm((f) => ({ ...f, host: e.target.value }))}
                placeholder="192.168.1.100"
                className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm w-40 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Port</label>
              <input
                required value={addForm.port}
                onChange={(e) => setAddForm((f) => ({ ...f, port: e.target.value }))}
                className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm w-24 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Priority (optional)</label>
              <input
                value={addForm.priority}
                onChange={(e) => setAddForm((f) => ({ ...f, priority: e.target.value }))}
                placeholder="auto"
                className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm w-24 focus:outline-none focus:border-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading === "add"}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors"
            >
              {loading === "add" ? "Adding…" : "Register"}
            </button>
            <button type="button" onClick={() => setShowAdd(false)} className="text-sm text-gray-500 hover:text-gray-300">
              Cancel
            </button>
          </form>
        )}

        {/* Node grid */}
        {masters.length > 0 && (
          <>
            <div>
              <p className="text-xs font-semibold text-yellow-500 uppercase tracking-widest mb-3">Masters</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {masters.map((n) => (
                  <NodeCard
                    key={n.node_id}
                    node={n}
                    onFailover={handleFailover}
                    onRemove={handleRemove}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-purple-500 uppercase tracking-widest mb-3">Replicas</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {replicas.map((n) => (
                  <NodeCard
                    key={n.node_id}
                    node={n}
                    onFailover={handleFailover}
                    onRemove={handleRemove}
                  />
                ))}
              </div>
            </div>
          </>
        )}

        {nodes.length === 0 && (
          <div className="text-center py-20 text-gray-600">Connecting to cluster…</div>
        )}

        {/* Event log */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 h-64">
          <EventLog events={events} onClear={clearEvents} />
        </div>

      </main>

      {toast && <Toast {...toast} />}
    </div>
  );
}
