import clsx from "clsx";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Megaphone, RefreshCw, Send, XCircle } from "lucide-react";
import { timeAgo } from "../../components/LessonCard";
import { ErrorBox, PageLoader, Spinner, errText, useToast } from "../../components/ui";
import { get, post } from "../../lib/api";

interface Overview {
  users: number;
  registered: number;
  with_telegram: number;
  active_7d: number;
  active_1d: number;
  blocked: number;
  lessons: Record<string, number>;
  raw_items: Record<string, number>;
  done_total: number;
  tutor_questions_7d: number;
  daily: { day: string; done: number; new_users: number }[];
  running: string[];
}

interface Job {
  id: number;
  job: string;
  ok: boolean;
  message: string;
  created_at: string;
}

const JOB_NAMES: Record<string, string> = {
  collect: "Yig'ish",
  daily: "Ertalabki yuborish",
  broadcast: "Xabar tarqatish",
};

export default function AdminOverview() {
  const qc = useQueryClient();
  const toast = useToast();
  const ov = useQuery({ queryKey: ["admin", "overview"], queryFn: () => get<Overview>("/admin/overview"), refetchInterval: 15000 });
  const jobs = useQuery({ queryKey: ["admin", "jobs"], queryFn: () => get<Job[]>("/admin/jobs"), refetchInterval: 15000 });
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  async function run(name: string, path: string, body: unknown = {}) {
    setBusy(name);
    try {
      await post(path, body);
      toast("Ish boshlandi — natija jurnalda ko'rinadi", "info");
      setTimeout(() => qc.invalidateQueries({ queryKey: ["admin"] }), 1500);
    } catch (e) {
      toast(errText(e), "error");
    } finally {
      setBusy(null);
    }
  }

  if (ov.isLoading) return <PageLoader />;
  if (ov.error || !ov.data) return <ErrorBox error={ov.error} retry={() => ov.refetch()} />;
  const d = ov.data;
  const max = Math.max(1, ...d.daily.map((x) => x.done));

  const cards = [
    { label: "Foydalanuvchilar", value: d.users, hint: `${d.registered} ro'yxatdan o'tgan` },
    { label: "Faol (7 kun)", value: d.active_7d, hint: `bugun ${d.active_1d}` },
    { label: "Telegram ulangan", value: d.with_telegram, hint: `${d.blocked} bloklagan` },
    { label: "Nashr qilingan darslar", value: d.lessons.published ?? 0, hint: `${d.lessons.draft ?? 0} qoralama` },
    { label: "Bajarilgan topshiriqlar", value: d.done_total, hint: "jami" },
    { label: "Ustozga savollar", value: d.tutor_questions_7d, hint: "7 kunda" },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => (
          <div key={c.label} className="card p-4">
            <div className="text-2xl font-extrabold">{c.value}</div>
            <div className="text-xs font-medium">{c.label}</div>
            <div className="text-[11px] text-muted">{c.hint}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h3 className="font-bold">Bajarilgan topshiriqlar — 14 kun</h3>
          <div className="mt-4 flex h-36 gap-1.5">
            {d.daily.map((x) => (
              <div key={x.day} className="group relative flex flex-1 flex-col items-center justify-end">
                <div
                  className="w-full rounded-t-md bg-accent/80 transition group-hover:bg-accent"
                  style={{ height: `${Math.max(2, (x.done / max) * 100)}%` }}
                />
                <span className="pointer-events-none absolute -top-6 hidden rounded bg-ink px-1.5 py-0.5 text-[10px] text-bg group-hover:block">
                  {x.done} · +{x.new_users} foyd.
                </span>
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-muted">
            <span>{d.daily[0]?.day.slice(5)}</span>
            <span>{d.daily[d.daily.length - 1]?.day.slice(5)}</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
            <span className="font-semibold text-ink">Yangiliklar oqimi:</span>
            {Object.entries(d.raw_items).map(([k, v]) => (
              <span key={k} className="badge">
                {k}: {v}
              </span>
            ))}
          </div>
        </div>

        <div className="card space-y-3 p-5">
          <h3 className="font-bold">Amallar</h3>
          <button className="btn-ghost w-full" disabled={!!busy || d.running.includes("collect")} onClick={() => run("collect", "/admin/jobs/collect")}>
            {busy === "collect" || d.running.includes("collect") ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
            Yangiliklarni hozir yig'ish
          </button>
          <button className="btn-ghost w-full" disabled={!!busy || d.running.includes("daily")} onClick={() => run("daily", "/admin/jobs/daily", { force: true })}>
            {busy === "daily" ? <Spinner className="h-4 w-4" /> : <Send className="h-4 w-4" />}
            Ertalabki darslarni hozir yuborish
          </button>
          <div className="border-t border-line pt-3">
            <label className="label">Hammaga xabar (Telegram)</label>
            <textarea className="input min-h-[80px]" value={text} onChange={(e) => setText(e.target.value)} placeholder="Matn (HTML: <b>, <i>, <a>)" />
            <button
              className="btn-primary mt-2 w-full"
              disabled={!text.trim() || !!busy}
              onClick={() => {
                if (window.confirm("Xabar barcha foydalanuvchilarga yuborilsinmi?")) {
                  run("broadcast", "/admin/broadcast", { text });
                  setText("");
                }
              }}
            >
              <Megaphone className="h-4 w-4" /> Yuborish
            </button>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <h3 className="font-bold">Ishlar jurnali</h3>
        <ul className="mt-3 divide-y divide-line">
          {(jobs.data ?? []).map((j) => (
            <li key={j.id} className="flex gap-3 py-2.5 text-sm">
              {j.ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-good" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-bad" />}
              <div className="min-w-0 flex-1">
                <div className="flex gap-2">
                  <span className="font-semibold">{JOB_NAMES[j.job] ?? j.job}</span>
                  <span className="text-xs text-muted">{timeAgo(j.created_at)}</span>
                </div>
                <p className={clsx("break-words text-xs text-muted", !j.ok && "whitespace-pre-wrap font-mono")}>{j.message.slice(0, 600)}</p>
              </div>
            </li>
          ))}
          {jobs.data?.length === 0 && <li className="py-3 text-sm text-muted">Hali ishlar bajarilmagan.</li>}
        </ul>
      </div>
    </div>
  );
}
