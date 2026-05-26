"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/layout/Navbar";
import { getLivraisons, createLivraison, updateLivraison, deleteLivraison } from "@/lib/api";
import type { Livraison } from "@/types";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";

function Toast({ msg, ok }: { msg: string; ok: boolean }) {
  return (
    <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-sm font-medium ${ok ? "bg-green-600" : "bg-red-600"} text-white`}>
      {msg}
    </div>
  );
}

const today = new Date().toISOString().slice(0, 10);
const empty: Livraison = { no_livraison: 0, date_livraison: today };

export default function LivraisonsPage() {
  const [rows, setRows]         = useState<Livraison[]>([]);
  const [form, setForm]         = useState<Livraison>(empty);
  const [editing, setEditing]   = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [toast, setToast]       = useState<{ msg: string; ok: boolean } | null>(null);

  function notify(msg: string, ok = true) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  async function load() {
    try { setRows(await getLivraisons()); } catch { /* ignore */ }
  }
  useEffect(() => { load(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      if (editing !== null) {
        await updateLivraison(editing, form);
        notify("Livraison updated");
      } else {
        await createLivraison(form);
        notify("Livraison created");
      }
      setShowForm(false); setEditing(null); setForm(empty);
      await load();
    } catch (err) {
      notify((err as Error).message, false);
    } finally { setLoading(false); }
  }

  async function handleDelete(id: number) {
    if (!confirm(`Delete livraison ${id}?`)) return;
    try { await deleteLivraison(id); notify("Livraison deleted"); await load(); }
    catch (err) { notify((err as Error).message, false); }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Livraisons" subtitle="CRUD — distributed on Redis cluster" />

      <main className="flex-1 overflow-y-auto p-6 space-y-5">

        {showForm ? (
          <form onSubmit={handleSubmit} className="rounded-xl border border-gray-700 bg-gray-900 p-5 space-y-4">
            <p className="text-sm font-semibold text-gray-200">{editing ? "Edit Livraison" : "New Livraison"}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Livraison ID</label>
                <input required type="number" value={form.no_livraison || ""}
                  onChange={(e) => setForm((f) => ({ ...f, no_livraison: +e.target.value }))}
                  disabled={editing !== null}
                  className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500 disabled:opacity-40"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Delivery Date</label>
                <input required type="date" value={form.date_livraison}
                  onChange={(e) => setForm((f) => ({ ...f, date_livraison: e.target.value }))}
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
            <Plus size={14} /> Add Livraison
          </button>
        )}

        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-gray-600 uppercase tracking-wider border-b border-gray-800">
                {["ID","Delivery Date","Actions"].map((h) => <th key={h} className="text-left px-4 py-3">{h}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {rows.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-600">No livraisons yet.</td></tr>}
              {rows.map((l) => (
                <tr key={l.no_livraison} className="hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-300">{l.no_livraison}</td>
                  <td className="px-4 py-3 text-white">{l.date_livraison}</td>
                  <td className="px-4 py-3 flex gap-2">
                    <button onClick={() => { setForm(l); setEditing(l.no_livraison); setShowForm(true); }}
                      className="p-1.5 rounded bg-gray-700 hover:bg-blue-600/40 text-gray-400 hover:text-blue-400 transition-colors"><Pencil size={13} /></button>
                    <button onClick={() => handleDelete(l.no_livraison)}
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
