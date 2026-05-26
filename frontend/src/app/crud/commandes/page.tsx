"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/layout/Navbar";
import { getCommandes, createCommande, updateCommande, deleteCommande } from "@/lib/api";
import type { Commande } from "@/types";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";

function Toast({ msg, ok }: { msg: string; ok: boolean }) {
  return (
    <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-sm font-medium ${ok ? "bg-green-600" : "bg-red-600"} text-white`}>
      {msg}
    </div>
  );
}

const today = new Date().toISOString().slice(0, 10);
const empty: Commande = { no_commande: 0, date_commande: today, no_client: 0 };

export default function CommandesPage() {
  const [rows, setRows]         = useState<Commande[]>([]);
  const [form, setForm]         = useState<Commande>(empty);
  const [editing, setEditing]   = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [toast, setToast]       = useState<{ msg: string; ok: boolean } | null>(null);

  function notify(msg: string, ok = true) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  async function load() {
    try { setRows(await getCommandes()); } catch { /* ignore */ }
  }
  useEffect(() => { load(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      if (editing !== null) {
        await updateCommande(editing, form);
        notify("Commande updated");
      } else {
        await createCommande(form);
        notify("Commande created");
      }
      setShowForm(false); setEditing(null); setForm(empty);
      await load();
    } catch (err) {
      notify((err as Error).message, false);
    } finally { setLoading(false); }
  }

  async function handleDelete(id: number) {
    if (!confirm(`Delete commande ${id}?`)) return;
    try { await deleteCommande(id); notify("Commande deleted"); await load(); }
    catch (err) { notify((err as Error).message, false); }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Commandes" subtitle="CRUD — distributed on Redis cluster" />

      <main className="flex-1 overflow-y-auto p-6 space-y-5">

        {showForm ? (
          <form onSubmit={handleSubmit} className="rounded-xl border border-gray-700 bg-gray-900 p-5 space-y-4">
            <p className="text-sm font-semibold text-gray-200">{editing ? "Edit Commande" : "New Commande"}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Commande ID</label>
                <input required type="number" value={form.no_commande || ""}
                  onChange={(e) => setForm((f) => ({ ...f, no_commande: +e.target.value }))}
                  disabled={editing !== null}
                  className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500 disabled:opacity-40"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Date</label>
                <input required type="date" value={form.date_commande}
                  onChange={(e) => setForm((f) => ({ ...f, date_commande: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Client ID</label>
                <input required type="number" value={form.no_client || ""}
                  onChange={(e) => setForm((f) => ({ ...f, no_client: +e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition-colors">
                <Check size={14} /> {loading ? "Saving…" : "Save"}
              </button>
              <button type="button" onClick={() => { setShowForm(false); setEditing(null); setForm(empty); }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm transition-colors">
                <X size={14} /> Cancel
              </button>
            </div>
          </form>
        ) : (
          <button onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors">
            <Plus size={14} /> Add Commande
          </button>
        )}

        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-gray-600 uppercase tracking-wider border-b border-gray-800">
                {["ID","Date","Client ID","Actions"].map((h) => <th key={h} className="text-left px-4 py-3">{h}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {rows.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-600">No commandes yet.</td></tr>}
              {rows.map((c) => (
                <tr key={c.no_commande} className="hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-300">{c.no_commande}</td>
                  <td className="px-4 py-3 text-white">{c.date_commande}</td>
                  <td className="px-4 py-3 text-blue-400">{c.no_client}</td>
                  <td className="px-4 py-3 flex gap-2">
                    <button onClick={() => { setForm(c); setEditing(c.no_commande); setShowForm(true); }}
                      className="p-1.5 rounded bg-gray-700 hover:bg-blue-600/40 text-gray-400 hover:text-blue-400 transition-colors"><Pencil size={13} /></button>
                    <button onClick={() => handleDelete(c.no_commande)}
                      className="p-1.5 rounded bg-gray-700 hover:bg-red-600/40 text-gray-400 hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>

      {toast && <Toast {...toast} />}
    </div>
  );
}
