"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/layout/Navbar";
import { getArticles, createArticle, updateArticle, deleteArticle } from "@/lib/api";
import type { Article } from "@/types";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";

function Toast({ msg, ok }: { msg: string; ok: boolean }) {
  return (
    <div className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-xl text-sm font-medium ${ok ? "bg-green-600" : "bg-red-600"} text-white`}>
      {msg}
    </div>
  );
}

const empty: Article = { no_article: 0, description: "", prix_unitaire: 0, quantite_en_stock: 0 };

export default function ArticlesPage() {
  const [rows, setRows]       = useState<Article[]>([]);
  const [form, setForm]       = useState<Article>(empty);
  const [editing, setEditing] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast]     = useState<{ msg: string; ok: boolean } | null>(null);

  function notify(msg: string, ok = true) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  async function load() {
    try { setRows(await getArticles()); } catch { /* ignore */ }
  }

  useEffect(() => { load(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      if (editing !== null) {
        await updateArticle(editing, form);
        notify("Article updated");
      } else {
        await createArticle(form);
        notify("Article created");
      }
      setShowForm(false); setEditing(null); setForm(empty);
      await load();
    } catch (err) {
      notify((err as Error).message, false);
    } finally { setLoading(false); }
  }

  async function handleDelete(id: number) {
    if (!confirm(`Delete article ${id}?`)) return;
    try { await deleteArticle(id); notify("Article deleted"); await load(); }
    catch (err) { notify((err as Error).message, false); }
  }

  function startEdit(a: Article) {
    setForm(a); setEditing(a.no_article); setShowForm(true);
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Navbar title="Articles" subtitle="CRUD — distributed on Redis cluster" />

      <main className="flex-1 overflow-y-auto p-6 space-y-5">

        {showForm ? (
          <form onSubmit={handleSubmit} className="rounded-xl border border-gray-700 bg-gray-900 p-5 space-y-4">
            <p className="text-sm font-semibold text-gray-200">{editing ? "Edit Article" : "New Article"}</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { key: "no_article", label: "Article ID", type: "number", disabled: editing !== null },
                { key: "description", label: "Description", type: "text" },
                { key: "prix_unitaire", label: "Unit Price", type: "number" },
                { key: "quantite_en_stock", label: "Stock", type: "number" },
              ].map(({ key, label, type, disabled }) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">{label}</label>
                  <input
                    required type={type}
                    value={(form as Record<string, unknown>)[key] as string | number}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: type === "number" ? +e.target.value : e.target.value }))}
                    disabled={!!disabled}
                    className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm focus:outline-none focus:border-blue-500 disabled:opacity-40"
                  />
                </div>
              ))}
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
            <Plus size={14} /> Add Article
          </button>
        )}

        <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-gray-600 uppercase tracking-wider border-b border-gray-800 bg-gray-900/80">
                {["ID","Description","Price","Stock","Actions"].map((h) => <th key={h} className="text-left px-4 py-3">{h}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {rows.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-600">No articles yet.</td></tr>}
              {rows.map((a) => (
                <tr key={a.no_article} className="hover:bg-gray-800/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-300">{a.no_article}</td>
                  <td className="px-4 py-3 text-white">{a.description}</td>
                  <td className="px-4 py-3 text-green-400">${a.prix_unitaire.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-400">{a.quantite_en_stock}</td>
                  <td className="px-4 py-3 flex gap-2">
                    <button onClick={() => startEdit(a)} className="p-1.5 rounded bg-gray-700 hover:bg-blue-600/40 text-gray-400 hover:text-blue-400 transition-colors"><Pencil size={13} /></button>
                    <button onClick={() => handleDelete(a.no_article)} className="p-1.5 rounded bg-gray-700 hover:bg-red-600/40 text-gray-400 hover:text-red-400 transition-colors"><Trash2 size={13} /></button>
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
