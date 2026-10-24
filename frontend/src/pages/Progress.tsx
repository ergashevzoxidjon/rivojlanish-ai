import clsx from "clsx";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, BookOpenCheck, Brain, Flame, Target, Trophy } from "lucide-react";
import { topicStyle } from "../components/LessonCard";
import { ErrorBox, PageHeader, PageLoader, ProgressBar } from "../components/ui";
import { get } from "../lib/api";
import type { Stats } from "../lib/types";

const WEEKDAYS = ["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"];

export default function Progress() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => get<Stats>("/me/stats") });
  const board = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => get<{ place: number; name: string; xp: number; rank: string; me: boolean }[]>("/leaderboard"),
  });

  if (stats.isLoading) return <PageLoader />;
  if (stats.error || !stats.data) return <ErrorBox error={stats.error} retry={() => stats.refetch()} />;
  const s = stats.data;
  const rank = s.rank;
  const maxWeek = Math.max(1, ...s.week.map((w) => w.done + w.read));

  return (
    <div className="space-y-6">
      <PageHeader title="Progress" subtitle="O'rganish yo'lingiz raqamlarda" />

      {/* Unvon */}
      <div className="card relative overflow-hidden p-6">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-accent/15 blur-2xl" />
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-accent-ink">
            <Trophy className="h-7 w-7" />
          </span>
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Unvoningiz</div>
            <div className="text-2xl font-extrabold">{rank.name}</div>
            <div className="text-sm text-muted">
              Daraja: <b className="text-ink">{s.level_name}</b> — test natijalaringizga qarab avtomatik o'zgaradi
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-extrabold text-accent">{rank.xp}</div>
            <div className="text-xs text-muted">XP</div>
          </div>
        </div>
        {rank.next_xp && (
          <div className="mt-5">
            <ProgressBar value={rank.xp - rank.floor} max={rank.next_xp - rank.floor} />
            <div className="mt-1.5 flex justify-between text-xs text-muted">
              <span>{rank.name}</span>
              <span>
                {rank.next_name} · yana {rank.next_xp - rank.xp} XP
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric icon={Flame} tone="text-warn bg-warn/10" label="Ketma-ket kun" value={s.streak} hint={`Rekord: ${s.best_streak}`} />
        <Metric icon={BookOpenCheck} tone="text-good bg-good/10" label="Bajarilgan" value={s.done} hint={`${s.read} ta o'qilgan`} />
        <Metric icon={Target} tone="text-accent bg-accent/10" label="Test aniqligi" value={`${s.quiz_accuracy}%`} hint={`${s.quizzes} ta test`} />
        <Metric icon={Brain} tone="text-[#0ea5a3] bg-[#0ea5a3]/10" label="Takrorlangan" value={s.reviews_done} hint={`${s.reviews_due} ta kutmoqda`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Hafta */}
        <div className="card p-5">
          <h2 className="font-bold">So'nggi 7 kun</h2>
          <p className="text-xs text-muted">Bajarilgan topshiriqlar va o'qilgan darslar</p>
          <div className="mt-5 flex h-40 gap-3">
            {s.week.map((w) => {
              const d = new Date(w.day + "T00:00:00");
              const total = w.done + w.read;
              return (
                <div key={w.day} className="flex flex-1 flex-col items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-muted">{total || ""}</span>
                  <div className="flex w-full flex-1 flex-col justify-end overflow-hidden rounded-lg bg-line/40">
                    <div className="bg-accent/40 transition-all" style={{ height: `${(w.read / maxWeek) * 100}%` }} />
                    <div className="bg-accent transition-all" style={{ height: `${(w.done / maxWeek) * 100}%` }} />
                  </div>
                  <span className="text-[11px] text-muted">{WEEKDAYS[d.getDay()]}</span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex gap-4 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5">
              <i className="h-2.5 w-2.5 rounded-sm bg-accent" /> Bajarilgan
            </span>
            <span className="inline-flex items-center gap-1.5">
              <i className="h-2.5 w-2.5 rounded-sm bg-accent/40" /> O'qilgan
            </span>
          </div>
        </div>

        {/* Mavzular */}
        <div className="card p-5">
          <h2 className="font-bold">Mavzular bo'yicha</h2>
          <p className="text-xs text-muted">Bajarilgan / jami nashr qilingan darslar</p>
          <div className="mt-5 space-y-5">
            {s.by_topic.map((t) => {
              const Icon = topicStyle[t.key].icon;
              return (
                <div key={t.key}>
                  <div className="mb-1.5 flex items-center gap-2 text-sm">
                    <Icon className="h-4 w-4 text-muted" />
                    <span className="flex-1 font-medium">{t.name}</span>
                    <span className="text-muted">
                      {t.done} / {t.total}
                    </span>
                  </div>
                  <ProgressBar value={t.done} max={t.total} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Yutuqlar */}
      <div className="card p-5">
        <h2 className="flex items-center gap-2 font-bold">
          <Award className="h-5 w-5 text-accent" /> Yutuqlar
          <span className="text-sm font-medium text-muted">
            {s.achievements.filter((a) => a.earned).length} / {s.achievements.length}
          </span>
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {s.achievements.map((a) => (
            <div
              key={a.key}
              className={clsx("rounded-xl border p-3 text-center transition", a.earned ? "border-accent/40 bg-accent/5" : "border-line opacity-50 grayscale")}
            >
              <div className="text-3xl">{a.icon}</div>
              <div className="mt-1 text-sm font-bold">{a.name}</div>
              <div className="text-[11px] text-muted">{a.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Reyting */}
      <div className="card p-5">
        <h2 className="flex items-center gap-2 font-bold">
          <Trophy className="h-5 w-5 text-warn" /> Eng faol o'quvchilar
        </h2>
        <ol className="mt-3 divide-y divide-line">
          {(board.data ?? []).map((r) => (
            <li key={r.place} className={clsx("flex items-center gap-3 py-2.5 text-sm", r.me && "font-bold text-accent")}>
              <span className="w-7 text-center">{["🥇", "🥈", "🥉"][r.place - 1] ?? r.place}</span>
              <span className="flex-1">
                {r.name} {r.me && "(siz)"}
              </span>
              <span className="text-xs text-muted">{r.rank}</span>
              <span className="w-16 text-right font-semibold">{r.xp} XP</span>
            </li>
          ))}
          {board.data?.length === 0 && <li className="py-3 text-sm text-muted">Reyting hali bo'sh — birinchi bo'ling!</li>}
        </ol>
      </div>
    </div>
  );
}

function Metric({
  icon: Icon,
  tone,
  label,
  value,
  hint,
}: {
  icon: typeof Flame;
  tone: string;
  label: string;
  value: ReactNode;
  hint: string;
}) {
  return (
    <div className="card p-4">
      <span className={clsx("inline-flex rounded-xl p-2", tone)}>
        <Icon className="h-5 w-5" />
      </span>
      <div className="mt-2 text-2xl font-extrabold">{value}</div>
      <div className="text-xs font-medium">{label}</div>
      <div className="text-[11px] text-muted">{hint}</div>
    </div>
  );
}
