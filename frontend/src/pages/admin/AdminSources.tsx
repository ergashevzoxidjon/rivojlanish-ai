import clsx from "clsx";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Plus, RotateCcw } from "lucide-react";
import { timeAgo } from "../../components/LessonCard";
import { ErrorBox, PageLoader, Toggle, errText, useToast } from "../../components/ui";
import { get, post, put, qs } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Topic } from "../../lib/types";

interface Source {
  id: number;
  name: string;
  url: string;
  kind: "rss" | "html";
  topic: Topic;
  tool: string;
  active: boolean;
  last_checked_at: string | null;
  last_error: string | null;
  items: number;
  lessons: number;
}

interface RawItem {
  id: number;
  title: string;
  url: string;
  status: string;
  note: string | null;
  source: string;
  created_at: string;
}

const RAW_STATUS = ["", "new", "lesson", "skipped", "error"];
const RAW_LABEL: Record<string, string> = { "": "Hammasi", new: "Yangi", lesson: "Darsga aylandi", skipped: "O'tkazildi", error: "Xato" };

export default function AdminSources() {
  const qc = useQueryClient();
  const toast = useToast();
  const { meta } = useAuth();
  const sources = useQuery({ queryKey: ["admin", "sources"], queryFn: () => get<Source[]>("/admin/sources") });
  const [rawStatus, setRawStatus] = useState("");
  const raw = useQuery({
    queryKey: ["admin", "raw", rawStatus],
    queryFn: () => get<RawItem[]>(`/admin/raw-items${qs({ status: rawStatus })}`),
  });
  const [form, setForm] = useState({ name: "", url: "", kind: "rss", topic: "chat", tool: "" });

  async function add() {
    try {
      await post("/admin/sources", { ...form, active: true });
      setForm({ name: "", url: "", kind: "rss", topic: "chat", tool: "" });
      toast("Manba qo'shildi");
      qc.invalidateQueries({ queryKey: ["admin", "sources"] });
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  async function toggle(s: Source) {
    await put(`/admin/sources/${s.id}`, { name: s.name, url: s.url, kind: s.kind, topic: s.topic, tool: s.tool, active: !s.active });
    qc.invalidateQueries({ queryKey: ["admin", "sources"] });
  }

  async function retry(id: number) {
    await post(`/admin/raw-items/${id}/retry`);
    toast("Keyingi yig'ishda qayta ko'riladi", "info");
    qc.invalidateQueries({ queryKey: ["admin", "raw"] });
  }

  if (sources.isLoading) return <PageLoader />;
  if (sources.error) return <ErrorBox error={sources.error} />;

  return (
    <div className="space-y-5">
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="p-3">Manba</th>
              <th className="p-3">Mavzu</th>
              <th className="p-3">Turi</th>
              <th className="p-3 text-right">Element / dars</th>
              <th className="p-3">Oxirgi tekshiruv</th>
              <th className="p-3">Faol</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {sources.data?.map((s) => (
              <tr key={s.id} className={clsx(!s.active && "opacity-50")}>
                <td className="p-3">
                  <div className="flex items-center gap-1.5 font-semibold">
                    {s.name}
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-muted hover:text-accent">
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                  <div className="text-xs text-muted">{s.tool}</div>
                  {s.last_error && (
                    <div className="mt-1 flex items-start gap-1 text-xs text-bad" title={s.last_error}>
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" /> <span className="line-clamp-1">{s.last_error}</span>
                    </div>
                  )}
                </td>
                <td className="p-3 text-xs">{meta?.topics.find((t) => t.key === s.topic)?.name}</td>
                <td className="p-3 text-xs uppercase">{s.kind}</td>
                <td className="p-3 text-right text-xs">
                  {s.items} / <b>{s.lessons}</b>
                </td>
                <td className="p-3 text-xs text-muted">{s.last_checked_at ? timeAgo(s.last_checked_at) : "—"}</td>
                <td className="p-3">
                  <Toggle checked={s.active} onChange={() => toggle(s)} label="Faol" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-5">
        <h3 className="font-bold">Yangi manba qo'shish</h3>
        <p className="text-xs text-muted">
          RSS/Atom (GitHub uchun: github.com/EGA/REPO/releases.atom) yoki oddiy sahifa (HTML — o'zgarishlar kuzatiladi)
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-6">
          <input className="input sm:col-span-2" placeholder="Nomi" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input sm:col-span-4" placeholder="https://..." value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <select className="input sm:col-span-1" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="rss">RSS</option>
            <option value="html">HTML</option>
          </select>
          <select className="input sm:col-span-2" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })}>
            {meta?.topics.map((t) => (
              <option key={t.key} value={t.key}>
                {t.name}
              </option>
            ))}
          </select>
          <input className="input sm:col-span-2" placeholder="Vosita (Claude...)" value={form.tool} onChange={(e) => setForm({ ...form, tool: e.target.value })} />
          <button className="btn-primary sm:col-span-1" disabled={!form.name || !form.url.startsWith("http")} onClick={add}>
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="card p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-auto font-bold">Topilgan yangiliklar</h3>
          {RAW_STATUS.map((s) => (
            <button key={s} className={clsx("chip", rawStatus === s && "chip-on")} onClick={() => setRawStatus(s)}>
              {RAW_LABEL[s]}
            </button>
          ))}
        </div>
        <ul className="mt-3 divide-y divide-line">
          {raw.data?.map((r) => (
            <li key={r.id} className="flex items-start gap-3 py-2.5 text-sm">
              <div className="min-w-0 flex-1">
                <a href={r.url} target="_blank" rel="noreferrer" className="font-medium hover:text-accent">
                  {r.title}
                </a>
                <div className="text-xs text-muted">
                  {r.source} · {RAW_LABEL[r.status] ?? r.status} · {timeAgo(r.created_at)}
                  {r.note && ` · ${r.note}`}
                </div>
              </div>
              {(r.status === "error" || r.status === "skipped") && (
                <button className="text-muted hover:text-accent" title="Qayta ko'rish" onClick={() => retry(r.id)}>
                  <RotateCcw className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
          {raw.data?.length === 0 && <li className="py-3 text-sm text-muted">Bo'sh.</li>}
        </ul>
      </div>
    </div>
  );
}
