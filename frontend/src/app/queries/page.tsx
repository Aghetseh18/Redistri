"use client";
import { useState } from "react";
import Navbar from "@/components/layout/Navbar";
import {
  joinCommande, groupByCommandesClient, groupByQuantiteArticle, entityDistribution,
  setupReplication, stopReplication, replicationStatus, demoReplication,
} from "@/lib/api";
import { GitMerge, BarChart2, Play, Server, Info, Database, CheckCircle, XCircle } from "lucide-react";

function NodeBadge({ nodeId }: { nodeId: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 font-mono">
      <Server size={9} />
      {nodeId}
    </span>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 space-y-4">
      <div className="flex items-center gap-2">
        {icon}
        <p className="text-sm font-semibold text-gray-200">{title}</p>
      </div>
      {children}
    </div>
  );
}

export default function QueriesPage() {
  const [joinId, setJoinId]   = useState("1");
  const [joinRes, setJoinRes] = useState<Record<string, unknown> | null>(null);
  const [joinLoading, setJoinLoading] = useState(false);

  const [gbcRes, setGbcRes] = useState<Record<string, unknown> | null>(null);
  const [gbcLoading, setGbcLoading] = useState(false);

  const [gbaRes, setGbaRes] = useState<Record<string, unknown> | null>(null);
  const [gbaLoading, setGbaLoading] = useState(false);

  const [distRes, setDistRes] = useState<Record<string, unknown> | null>(null);
  const [distLoading, setDistLoading] = useState(false);

  // Replication state
  const [replMasterId,  setReplMasterId]  = useState("localhost:6379");
  const [replReplicaId, setReplReplicaId] = useState("10.108.135.244:7001");
  const [replSetupRes,  setReplSetupRes]  = useState<Record<string, unknown> | null>(null);
  const [replSetupLoading, setReplSetupLoading] = useState(false);
  const [replStopLoading,  setReplStopLoading]  = useState(false);
  const [replStatusRes, setReplStatusRes] = useState<Record<string, unknown> | null>(null);
  const [replStatusLoading, setReplStatusLoading] = useState(false);
  const [replDemoRes,   setReplDemoRes]   = useState<Record<string, unknown> | null>(null);
  const [replDemoLoading, setReplDemoLoading] = useState(false);

  async function runJoin() {
    setJoinLoading(true);
    try { setJoinRes(await joinCommande(parseInt(joinId))); }
    catch (e) { alert((e as Error).message); }
    finally { setJoinLoading(false); }
  }

  async function runGroupByClient() {
    setGbcLoading(true);
    try { setGbcRes(await groupByCommandesClient()); }
    catch (e) { alert((e as Error).message); }
    finally { setGbcLoading(false); }
  }

  async function runGroupByArticle() {
    setGbaLoading(true);
    try { setGbaRes(await groupByQuantiteArticle()); }
    catch (e) { alert((e as Error).message); }
    finally { setGbaLoading(false); }
  }

  async function runDist() {
    setDistLoading(true);
    try { setDistRes(await entityDistribution()); }
    catch (e) { alert((e as Error).message); }
    finally { setDistLoading(false); }
  }

  async function runSetupReplication() {
    setReplSetupLoading(true);
    try { setReplSetupRes(await setupReplication(replMasterId.trim(), replReplicaId.trim())); }
    catch (e) { alert((e as Error).message); }
    finally { setReplSetupLoading(false); }
  }

  async function runStopReplication() {
    setReplStopLoading(true);
    try {
      await stopReplication(replReplicaId.trim());
      setReplSetupRes(null);
      alert("Replication stopped — replica is now independent.");
    }
    catch (e) { alert((e as Error).message); }
    finally { setReplStopLoading(false); }
  }

  async function runReplStatus() {
    setReplStatusLoading(true);
    try { setReplStatusRes(await replicationStatus()); }
    catch (e) { alert((e as Error).message); }
    finally { setReplStatusLoading(false); }
  }

  async function runReplDemo() {
    setReplDemoLoading(true);
    try { setReplDemoRes(await demoReplication(replMasterId.trim())); }
    catch (e) { alert((e as Error).message); }
    finally { setReplDemoLoading(false); }
  }

  type NodeSources = Record<string, string>;

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Distributed Queries" subtitle="Simulated JOIN and GROUP BY across Redis nodes" />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Explanation banner */}
        <div className="rounded-xl border border-blue-500/20 bg-blue-950/20 p-4 flex gap-3">
          <Info size={16} className="text-blue-400 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-200 space-y-1">
            <p className="font-semibold">Why no SQL JOIN in Redis?</p>
            <p className="text-blue-300/70 text-xs">
              Redis has no native JOIN. Each entity type lives on a different physical node.
              These queries fetch data from multiple nodes in sequence and aggregate in Python —
              simulating what a relational DB does in SQL. The <code className="text-blue-300">_node_sources</code> field
              in every response shows which machine provided each piece of data.
            </p>
          </div>
        </div>

        {/* Entity distribution */}
        <Section title="Write from one machine, Read from another" icon={<Server size={15} className="text-teal-400" />}>
          <p className="text-xs text-gray-500">
            Shows which physical Redis node (machine) stores each entity type.
            A write to /clients goes to the &quot;clients&quot; node; a read from /articles comes from the &quot;articles&quot; node.
          </p>
          <button onClick={runDist} disabled={distLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-700/40 hover:bg-teal-600/50 text-teal-300 text-sm font-medium transition-colors">
            <Play size={13} /> {distLoading ? "Running…" : "Show Entity Distribution"}
          </button>
          {distRes && (
            <div className="space-y-2">
              {Object.entries((distRes.entity_distribution ?? {}) as Record<string, { node_id: string; host: string; port: number; role: string; status: string }>).map(([entity, info]) => (
                <div key={entity} className="flex items-center gap-3 text-xs">
                  <span className="w-36 font-mono text-indigo-300">{entity}</span>
                  <span className="text-gray-500">→</span>
                  <NodeBadge nodeId={info.node_id} />
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${info.role === "master" ? "bg-yellow-500/20 text-yellow-300" : "bg-purple-500/20 text-purple-300"}`}>{info.role}</span>
                  <span className={`text-[10px] ${info.status === "healthy" ? "text-green-400" : "text-red-400"}`}>{info.status}</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* JOIN */}
        <Section title="JOIN Simulation — Full Order Details" icon={<GitMerge size={15} className="text-purple-400" />}>
          <p className="text-xs text-gray-500">
            Fetches one order and joins: Commande (node A) + Client (node B) + LigneCommandes (node C) + Articles (node D).
          </p>
          <div className="flex items-center gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Commande ID</label>
              <input type="number" value={joinId} onChange={(e) => setJoinId(e.target.value)}
                className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm w-28 focus:outline-none focus:border-blue-500"
              />
            </div>
            <button onClick={runJoin} disabled={joinLoading}
              className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-700/40 hover:bg-purple-600/50 text-purple-300 text-sm font-medium transition-colors">
              <Play size={13} /> {joinLoading ? "Running…" : "Run JOIN"}
            </button>
          </div>

          {joinRes && (
            <div className="space-y-4">
              {/* Node sources */}
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-gray-500">Data fetched from:</span>
                {Object.entries((joinRes._node_sources ?? {}) as NodeSources).map(([entity, nodeId]) => (
                  <span key={entity} className="text-xs text-gray-400">
                    <span className="text-indigo-400">{entity}</span> → <NodeBadge nodeId={nodeId} />
                  </span>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Commande */}
                <div className="rounded-lg border border-gray-700 p-3 space-y-1">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase">Commande</p>
                  {joinRes.commande
                    ? Object.entries(joinRes.commande as Record<string, unknown>).map(([k, v]) => (
                        <div key={k} className="flex gap-2 text-xs">
                          <span className="text-gray-500 w-32 shrink-0">{k}</span>
                          <span className="text-white">{String(v)}</span>
                        </div>
                      ))
                    : <p className="text-xs text-gray-600">Not found</p>
                  }
                </div>

                {/* Client */}
                <div className="rounded-lg border border-gray-700 p-3 space-y-1">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase">Client (JOIN)</p>
                  {joinRes.client
                    ? Object.entries(joinRes.client as Record<string, unknown>).map(([k, v]) => (
                        <div key={k} className="flex gap-2 text-xs">
                          <span className="text-gray-500 w-32 shrink-0">{k}</span>
                          <span className="text-white">{String(v)}</span>
                        </div>
                      ))
                    : <p className="text-xs text-gray-600">Client not found</p>
                  }
                </div>
              </div>

              {/* Lignes */}
              {(joinRes.lignes as unknown[]).length > 0 && (
                <div className="rounded-lg border border-gray-700 p-3">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">
                    Lignes Commande ({(joinRes.lignes as unknown[]).length}) — JOIN with Articles
                  </p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-600 border-b border-gray-800">
                        <th className="text-left pb-1">Article ID</th>
                        <th className="text-left pb-1">Qty</th>
                        <th className="text-left pb-1">Description</th>
                        <th className="text-left pb-1">Unit Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(joinRes.lignes as Record<string, unknown>[]).map((l, i) => {
                        const art = l.article as Record<string, unknown> | null;
                        return (
                          <tr key={i} className="border-t border-gray-800/50">
                            <td className="py-1 text-gray-300">{String(l.no_article)}</td>
                            <td className="py-1 text-white">{String(l.quantite)}</td>
                            <td className="py-1 text-gray-300">{art?.description as string ?? "—"}</td>
                            <td className="py-1 text-green-400">{art ? `$${(art.prix_unitaire as number).toFixed(2)}` : "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </Section>

        {/* GROUP BY client */}
        <Section title="GROUP BY — Orders per Client" icon={<BarChart2 size={15} className="text-orange-400" />}>
          <p className="text-xs text-gray-500">
            Reads all clients (node A) and all commandes (node B), then aggregates in Python — simulating SQL GROUP BY.
          </p>
          <button onClick={runGroupByClient} disabled={gbcLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-700/40 hover:bg-orange-600/50 text-orange-300 text-sm font-medium transition-colors">
            <Play size={13} /> {gbcLoading ? "Running…" : "Run GROUP BY Client"}
          </button>
          {gbcRes && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                Sources:
                {Object.entries((gbcRes._node_sources ?? {}) as NodeSources).map(([e, n]) => (
                  <span key={e}><span className="text-indigo-400">{e}</span> → <NodeBadge nodeId={n} /></span>
                ))}
              </div>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-600 border-b border-gray-800">
                    <th className="text-left pb-2">Client</th>
                    <th className="text-left pb-2">Phone</th>
                    <th className="text-left pb-2 text-center">Orders</th>
                    <th className="text-left pb-2">Order IDs</th>
                  </tr>
                </thead>
                <tbody>
                  {(gbcRes.results as { client: Record<string,unknown>; nb_commandes: number; commandes: number[] }[])
                    .sort((a, b) => b.nb_commandes - a.nb_commandes)
                    .map((row, i) => (
                      <tr key={i} className="border-t border-gray-800/50">
                        <td className="py-2 text-white">{String(row.client.nom_client)}</td>
                        <td className="py-2 text-gray-400">{String(row.client.no_telephone)}</td>
                        <td className="py-2 text-center">
                          <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 font-bold">
                            {row.nb_commandes}
                          </span>
                        </td>
                        <td className="py-2 text-gray-500 font-mono">{row.commandes.join(", ")}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        {/* GROUP BY article */}
        <Section title="GROUP BY — Quantity Ordered per Article" icon={<BarChart2 size={15} className="text-green-400" />}>
          <p className="text-xs text-gray-500">
            Reads all ligne_commandes (node A) and articles (node B), sums quantities per article — simulating SQL GROUP BY + SUM.
          </p>
          <button onClick={runGroupByArticle} disabled={gbaLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-700/40 hover:bg-green-600/50 text-green-300 text-sm font-medium transition-colors">
            <Play size={13} /> {gbaLoading ? "Running…" : "Run GROUP BY Article"}
          </button>
          {gbaRes && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                Sources:
                {Object.entries((gbaRes._node_sources ?? {}) as NodeSources).map(([e, n]) => (
                  <span key={e}><span className="text-indigo-400">{e}</span> → <NodeBadge nodeId={n} /></span>
                ))}
              </div>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-600 border-b border-gray-800">
                    <th className="text-left pb-2">Article</th>
                    <th className="text-left pb-2">Description</th>
                    <th className="text-left pb-2">Unit Price</th>
                    <th className="text-left pb-2 text-right">Total Qty Ordered</th>
                  </tr>
                </thead>
                <tbody>
                  {(gbaRes.results as { no_article: number; article: Record<string,unknown>|null; total_quantite_commandee: number }[])
                    .map((row, i) => (
                      <tr key={i} className="border-t border-gray-800/50">
                        <td className="py-2 font-mono text-gray-300">{row.no_article}</td>
                        <td className="py-2 text-white">{row.article?.description as string ?? "—"}</td>
                        <td className="py-2 text-green-400">{row.article ? `$${(row.article.prix_unitaire as number).toFixed(2)}` : "—"}</td>
                        <td className="py-2 text-right">
                          <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-300 font-bold">
                            {row.total_quantite_commandee}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        {/* Replication Demo */}
        <Section title="Redis Replication — Write on Master, Read from Replica" icon={<Database size={15} className="text-cyan-400" />}>
          <p className="text-xs text-gray-500">
            Configure real Redis replication using <code className="text-cyan-300">REPLICAOF</code>.
            Once set up, every key written to the master is mirrored to the replica in real time.
            The demo writes a test key to the master and reads it back from the replica.
          </p>

          {/* Setup form */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Master node_id</label>
              <input value={replMasterId} onChange={(e) => setReplMasterId(e.target.value)}
                className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm font-mono focus:outline-none focus:border-cyan-500"
                placeholder="localhost:6379" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">Replica node_id</label>
              <input value={replReplicaId} onChange={(e) => setReplReplicaId(e.target.value)}
                className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm font-mono focus:outline-none focus:border-cyan-500"
                placeholder="10.108.135.244:7001" />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button onClick={runSetupReplication} disabled={replSetupLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-700/40 hover:bg-cyan-600/50 text-cyan-300 text-sm font-medium transition-colors">
              <Play size={13} /> {replSetupLoading ? "Configuring…" : "Setup REPLICAOF"}
            </button>
            <button onClick={runStopReplication} disabled={replStopLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-700/30 hover:bg-red-600/40 text-red-300 text-sm font-medium transition-colors">
              {replStopLoading ? "Stopping…" : "Stop Replication"}
            </button>
            <button onClick={runReplStatus} disabled={replStatusLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700/40 hover:bg-gray-600/50 text-gray-300 text-sm font-medium transition-colors">
              <Info size={13} /> {replStatusLoading ? "Loading…" : "Replication Status"}
            </button>
            <button onClick={runReplDemo} disabled={replDemoLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-700/40 hover:bg-indigo-600/50 text-indigo-300 text-sm font-medium transition-colors">
              <Play size={13} /> {replDemoLoading ? "Running…" : "Run Write→Read Demo"}
            </button>
          </div>

          {replSetupRes && (
            <div className="rounded-lg border border-cyan-800/40 bg-cyan-950/20 p-3 text-xs space-y-1">
              <p className="font-semibold text-cyan-300">Replication configured</p>
              <p className="text-gray-400">Master: <span className="font-mono text-white">{String(replSetupRes.master)}</span></p>
              <p className="text-gray-400">Replica: <span className="font-mono text-white">{String(replSetupRes.replica)}</span></p>
              <p className="text-gray-400">Master IP used: <span className="font-mono text-white">{String(replSetupRes.master_host_used)}</span></p>
              <p className="text-gray-500 italic">Redis REPLICAOF sent — all writes to master are now mirrored to replica.</p>
            </div>
          )}

          {replDemoRes && (
            <div className={`rounded-lg border p-3 text-xs space-y-3 ${replDemoRes.replication_ok ? "border-green-700/40 bg-green-950/20" : "border-red-700/40 bg-red-950/20"}`}>
              <div className="flex items-center gap-2">
                {replDemoRes.replication_ok
                  ? <CheckCircle size={14} className="text-green-400" />
                  : <XCircle size={14} className="text-red-400" />
                }
                <p className={`font-semibold ${replDemoRes.replication_ok ? "text-green-300" : "text-red-300"}`}>
                  {replDemoRes.replication_ok ? "Replication OK — data crossed machines!" : "Replication failed or not yet configured"}
                </p>
                {replDemoRes.replication_lag_ms !== null && (
                  <span className="ml-auto text-gray-500">lag: {String(replDemoRes.replication_lag_ms)} ms</span>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <p className="font-semibold text-gray-400 uppercase text-[10px]">Write (Master)</p>
                  {replDemoRes.write && Object.entries(replDemoRes.write as Record<string, unknown>).map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="text-gray-500 w-16 shrink-0">{k}</span>
                      <span className="font-mono text-white text-[10px]">{String(v)}</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-1">
                  <p className="font-semibold text-gray-400 uppercase text-[10px]">Read (Replica)</p>
                  {replDemoRes.read && Object.entries(replDemoRes.read as Record<string, unknown>).map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="text-gray-500 w-16 shrink-0">{k}</span>
                      <span className="font-mono text-white text-[10px]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
              {replDemoRes.error && (
                <p className="text-red-400 italic">{String(replDemoRes.error)}</p>
              )}
            </div>
          )}

          {replStatusRes && (
            <div className="space-y-2">
              <p className="text-[10px] font-semibold text-gray-500 uppercase">Node Replication Info</p>
              {(replStatusRes.nodes as Record<string, unknown>[]).map((n, i) => (
                <div key={i} className="rounded-lg border border-gray-800 p-3 text-xs space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-indigo-300">{String(n.node_id)}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${n.redis_role === "master" ? "bg-yellow-500/20 text-yellow-300" : "bg-purple-500/20 text-purple-300"}`}>
                      {String(n.redis_role ?? "?")}
                    </span>
                    {n.master_link_status && (
                      <span className={`text-[10px] ${n.master_link_status === "up" ? "text-green-400" : "text-red-400"}`}>
                        link: {String(n.master_link_status)}
                      </span>
                    )}
                  </div>
                  {n.connected_slaves !== undefined && (
                    <p className="text-gray-500">Connected replicas: <span className="text-white">{String(n.connected_slaves)}</span></p>
                  )}
                  {n.master_repl_offset !== undefined && (
                    <p className="text-gray-500">Repl offset: <span className="font-mono text-white">{String(n.master_repl_offset)}</span></p>
                  )}
                  {n.master_last_io_seconds_ago !== undefined && (
                    <p className="text-gray-500">Last I/O: <span className="text-white">{String(n.master_last_io_seconds_ago)}s ago</span></p>
                  )}
                  {n.error && <p className="text-red-400 italic">{String(n.error)}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>

      </main>
    </div>
  );
}
