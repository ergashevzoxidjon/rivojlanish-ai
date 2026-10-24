import clsx from "clsx";
import { useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, Pencil, Plus, Sparkles, Trash2, Wand2 } from "lucide-react";
import { timeAgo } from "../../components/LessonCard";
import { Empty, ErrorBox, Markdown, PageLoader, Spinner, errText, useToast } from "../../components/ui";
import { del, get, post, put, qs } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Lesson, LessonFull, Level, Paged, QuizQuestion, Topic } from "../../lib/types";

const STATUS = [
  { key: "", label: "Hammasi" },
  { key: "draft", label: "Qoralama" },
  { key: "published", label: "Nashr" },
  { key: "rejected", label: "Rad" },
];

const statusTone: Record<string, string> = {
  draft: "bg-warn/10 text-warn",
  published: "bg-good/10 text-good",
  rejected: "bg-bad/10 text-bad",
};

const ORIGIN: Record<string, string> = { news: "Yangilik", on_demand: "So'rov", manual: "Qo'lda" };

export default function AdminLessons() {
  const [status, setStatus] = useState("draft");
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<LessonFull | "new" | null>(null);
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: ["admin", "lessons", status, q],
    queryFn: () => get<Paged<Lesson>>(`/admin/lessons${qs({ status, q })}`),
  });

  async function open(id: number) {
    setEditing(await get<LessonFull>(`/admin/lessons/${id}`));
  }

  if (editing)
    return (
      <LessonEditor
        initial={editing === "new" ? null : editing}
        onClose={() => {
          setEditing(null);
          qc.invalidateQueries({ queryKey: ["admin"] });
        }}
      />
    );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-xl border border-line bg-elevated p-1">
          {STATUS.map((s) => (
            <button
              key={s.key}
              onClick={() => setStatus(s.key)}
              className={clsx(
                "rounded-lg px-3 py-1.5 text-xs font-semibold",
                status === s.key ? "bg-surface text-ink shadow-sm" : "text-muted",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
        <input className="input w-full sm:w-60" placeholder="Sarlavha bo'yicha qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="flex w-full gap-2 sm:ml-auto sm:w-auto">
          <GenerateButton onCreated={setEditing} />
          <button className="btn-ghost" onClick={() => setEditing("new")}>
            <Plus className="h-4 w-4" /> Yangi
          </button>
        </div>
      </div>

      {list.isLoading ? (
        <PageLoader />
      ) : list.error ? (
        <ErrorBox error={list.error} />
      ) : list.data?.items.length ? (
        <div className="card divide-y divide-line">
          {list.data.items.map((l) => (
            <button key={l.id} onClick={() => open(l.id)} className="flex w-full items-center gap-3 p-4 text-left hover:bg-elevated">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                  <span className={clsx("badge", statusTone[l.status])}>{l.status}</span>
                  <span className="badge">{ORIGIN[l.origin]}</span>
                  <span>{l.topic_name}</span>·<span>{l.tool}</span>·<span>muhimlik {l.importance}</span>·
                  <span>{timeAgo(l.created_at)}</span>
                </div>
                <div className="mt-1 truncate font-semibold">{l.title}</div>
              </div>
              <Pencil className="h-4 w-4 shrink-0 text-muted" />
            </button>
          ))}
        </div>
      ) : (
        <Empty title="Darslar yo'q" text="Bu holatda dars topilmadi." />
      )}
    </div>
  );
}

function GenerateButton({ onCreated }: { onCreated: (l: LessonFull) => void }) {
  const { meta } = useAuth();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState<Topic>("chat");
  const [level, setLevel] = useState<Level>("beginner");
  const [busy, setBusy] = useState(false);

  async function go() {
    setBusy(true);
    try {
      onCreated(await post<LessonFull>("/admin/generate", { topic, level }));
    } catch (e) {
      toast(errText(e), "error");
    } finally {
      setBusy(false);
    }
  }

  if (!open)
    return (
      <button className="btn-soft flex-1 sm:flex-none" onClick={() => setOpen(true)}>
        <Wand2 className="h-4 w-4" /> AI bilan yozdirish
      </button>
    );
  return (
    <div className="flex flex-1 items-center gap-2">
      <select className="input py-2" value={topic} onChange={(e) => setTopic(e.target.value as Topic)}>
        {meta?.topics.map((t) => (
          <option key={t.key} value={t.key}>
            {t.name}
          </option>
        ))}
      </select>
      <select className="input py-2" value={level} onChange={(e) => setLevel(e.target.value as Level)}>
        {meta?.levels.map((l) => (
          <option key={l.key} value={l.key}>
            {l.name}
          </option>
        ))}
      </select>
      <button className="btn-primary shrink-0" disabled={busy} onClick={go}>
        {busy ? <Spinner className="h-4 w-4 text-accent-ink" /> : <Sparkles className="h-4 w-4" />}
      </button>
    </div>
  );
}

const EMPTY: Omit<LessonFull, "id" | "slug" | "progress" | "quiz_count" | "topic_name" | "level_name"> = {
  title: "",
  topic: "chat",
  tool: "",
  level: "beginner",
  minutes: 7,
  importance: 5,
  summary: "",
  body_md: "",
  task_md: "",
  source_url: "",
  origin: "manual",
  status: "draft",
  published_at: null,
  created_at: null,
  quiz: [],
};

function LessonEditor({ initial, onClose }: { initial: LessonFull | null; onClose: () => void }) {
  const { meta } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ ...EMPTY, ...(initial ?? {}) });
  const [id, setId] = useState<number | null>(initial?.id ?? null);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);

  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((x) => ({ ...x, [k]: v }));

  function payload(status?: string) {
    return {
      title: f.title,
      topic: f.topic,
      tool: f.tool,
      level: f.level,
      minutes: Number(f.minutes),
      importance: Number(f.importance),
      summary: f.summary,
      body_md: f.body_md,
      task_md: f.task_md,
      source_url: f.source_url,
      quiz: f.quiz,
      status,
    };
  }

  async function save(publish = false): Promise<number | null> {
    setBusy(true);
    try {
      const saved = id
        ? await put<LessonFull>(`/admin/lessons/${id}`, payload())
        : await post<LessonFull>("/admin/lessons", payload(publish ? "published" : undefined));
      setId(saved.id);
      if (publish && id) await post(`/admin/lessons/${saved.id}/publish`);
      toast(publish ? "Nashr qilindi" : "Saqlandi");
      if (publish) onClose();
      return saved.id;
    } catch (e) {
      toast(errText(e), "error");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function action(a: "reject" | "draft") {
    if (!id) return;
    await post(`/admin/lessons/${id}/${a}`);
    toast(a === "reject" ? "Rad etildi" : "Qoralamaga qaytarildi");
    onClose();
  }

  async function remove() {
    if (!id || !window.confirm("Dars butunlay o'chirilsinmi?")) return;
    await del(`/admin/lessons/${id}`);
    toast("O'chirildi");
    onClose();
  }

  function setQuiz(i: number, patchQ: Partial<QuizQuestion>) {
    set("quiz", f.quiz.map((q, j) => (j === i ? { ...q, ...patchQ } : q)));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={onClose} className="btn-ghost">
          <ArrowLeft className="h-4 w-4" /> Ro'yxat
        </button>
        {initial?.stats && (
          <span className="text-xs text-muted">
            Yuborilgan {initial.stats.sent} · o'qilgan {initial.stats.read} · bajarilgan {initial.stats.done}
          </span>
        )}
        <div className="ml-auto flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => setPreview(!preview)}>
            {preview ? <Pencil className="h-4 w-4" /> : <Eye className="h-4 w-4" />} {preview ? "Tahrirlash" : "Ko'rish"}
          </button>
          {id && f.status !== "rejected" && (
            <button className="btn-ghost text-bad" onClick={() => action("reject")}>
              Rad etish
            </button>
          )}
          {id && f.status === "published" && (
            <button className="btn-ghost" onClick={() => action("draft")}>
              Nashrdan olish
            </button>
          )}
          {id && (
            <button className="btn-ghost text-bad" onClick={remove} title="O'chirish">
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          <button className="btn-ghost" disabled={busy} onClick={() => save(false)}>
            Saqlash
          </button>
          {f.status !== "published" && (
            <button className="btn-primary" disabled={busy} onClick={() => save(true)}>
              Saqlash va nashr qilish
            </button>
          )}
        </div>
      </div>

      {preview ? (
        <div className="card p-6">
          <h1 className="text-2xl font-extrabold">{f.title}</h1>
          <p className="mt-3 rounded-xl bg-accent/5 p-3 text-sm">{f.summary}</p>
          <Markdown className="mt-4">{f.body_md}</Markdown>
          <h3 className="mt-6 font-bold">Topshiriq</h3>
          <Markdown className="prose-sm">{f.task_md}</Markdown>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card space-y-4 p-5 lg:col-span-2">
            <Field label="Sarlavha">
              <input className="input" value={f.title} onChange={(e) => set("title", e.target.value)} />
            </Field>
            <Field label="Bu nima? (qisqacha)">
              <textarea className="input min-h-[80px]" value={f.summary} onChange={(e) => set("summary", e.target.value)} />
            </Field>
            <Field label="Dars matni (Markdown)">
              <textarea className="input min-h-[320px] font-mono text-[13px]" value={f.body_md} onChange={(e) => set("body_md", e.target.value)} />
            </Field>
            <Field label="Amaliy topshiriq (Markdown)">
              <textarea className="input min-h-[100px]" value={f.task_md} onChange={(e) => set("task_md", e.target.value)} />
            </Field>
          </div>
          <div className="space-y-4">
            <div className="card space-y-3 p-5">
              <Field label="Mavzu">
                <select className="input" value={f.topic} onChange={(e) => set("topic", e.target.value as Topic)}>
                  {meta?.topics.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Vosita">
                <input className="input" value={f.tool} onChange={(e) => set("tool", e.target.value)} placeholder="Claude, Cursor, n8n..." />
              </Field>
              <Field label="Daraja">
                <select className="input" value={f.level} onChange={(e) => set("level", e.target.value as Level)}>
                  {meta?.levels.map((l) => (
                    <option key={l.key} value={l.key}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Daqiqa">
                  <input type="number" min={1} max={120} className="input" value={f.minutes} onChange={(e) => set("minutes", Number(e.target.value))} />
                </Field>
                <Field label="Muhimlik (1-10)">
                  <input type="number" min={1} max={10} className="input" value={f.importance} onChange={(e) => set("importance", Number(e.target.value))} />
                </Field>
              </div>
              <Field label="Manba URL">
                <input className="input" value={f.source_url} onChange={(e) => set("source_url", e.target.value)} />
              </Field>
            </div>

            <div className="card space-y-4 p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-bold">Test savollari</h3>
                <button
                  className="btn-soft px-3 py-1.5 text-xs"
                  onClick={() => set("quiz", [...f.quiz, { q: "", options: ["", "", ""], answer: 0, explain: "" }])}
                >
                  <Plus className="h-3.5 w-3.5" /> Savol
                </button>
              </div>
              {f.quiz.map((q, i) => (
                <div key={i} className="space-y-2 rounded-xl border border-line p-3">
                  <div className="flex gap-2">
                    <input className="input py-2" placeholder={`${i + 1}-savol`} value={q.q} onChange={(e) => setQuiz(i, { q: e.target.value })} />
                    <button className="text-muted hover:text-bad" onClick={() => set("quiz", f.quiz.filter((_, j) => j !== i))}>
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  {q.options.map((o, oi) => (
                    <label key={oi} className="flex items-center gap-2">
                      <input type="radio" name={`ans-${i}`} checked={q.answer === oi} onChange={() => setQuiz(i, { answer: oi })} />
                      <input
                        className="input py-1.5"
                        value={o}
                        placeholder={`Variant ${oi + 1}`}
                        onChange={(e) => setQuiz(i, { options: q.options.map((x, k) => (k === oi ? e.target.value : x)) })}
                      />
                    </label>
                  ))}
                  <input className="input py-1.5 text-xs" placeholder="Izoh (nega shu javob to'g'ri)" value={q.explain ?? ""} onChange={(e) => setQuiz(i, { explain: e.target.value })} />
                </div>
              ))}
              {f.quiz.length === 0 && <p className="text-xs text-muted">Test yo'q. Takrorlash uchun kamida 1 ta savol tavsiya etiladi.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  );
}
