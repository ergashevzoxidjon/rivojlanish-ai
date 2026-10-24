import clsx from "clsx";
import { useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, Check, Flame, Library, Send, Sparkles, Target, X } from "lucide-react";
import { Link } from "react-router-dom";
import LessonCard from "../components/LessonCard";
import { Empty, ErrorBox, ProgressBar, Skeleton, Spinner, errText, useToast } from "../components/ui";
import { get, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import { haptic } from "../lib/telegram";
import type { Lesson, Review, Stats } from "../lib/types";

interface TodayData {
  lessons: Lesson[];
  from_daily: boolean;
  reviews: Review[];
}

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "Xayrli tun";
  if (h < 12) return "Xayrli tong";
  if (h < 18) return "Xayrli kun";
  return "Xayrli kech";
}

export default function Today() {
  const { user, meta } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const today = useQuery({ queryKey: ["today"], queryFn: () => get<TodayData>("/today") });
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => get<Stats>("/me/stats") });
  const [extra, setExtra] = useState<Lesson[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);

  async function more() {
    setLoadingMore(true);
    try {
      const r = await post<{ generated: boolean; lessons: Lesson[] }>("/more");
      setExtra((xs) => [...xs, ...r.lessons]);
      haptic("success");
      toast(r.generated ? "Siz uchun yangi dars yozildi ✨" : `${r.lessons.length} ta yangi dars qo'shildi`);
    } catch (e) {
      toast(errText(e), "error");
    } finally {
      setLoadingMore(false);
    }
  }

  const s = stats.data;
  const rank = user?.rank;
  const first = (user?.name || "").split(" ")[0];
  const lessons = [...(today.data?.lessons ?? []), ...extra.filter((x) => !today.data?.lessons.some((l) => l.id === x.id))];
  const doneToday = lessons.filter((l) => l.progress.done).length;

  return (
    <div className="space-y-6">
      <section className="animate-fade-up">
        <p className="text-sm font-medium text-muted">{greeting()},</p>
        <h1 className="text-3xl font-extrabold tracking-tight">{first} 👋</h1>
      </section>

      {/* Ko'rsatkichlar */}
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard icon={<Flame className="h-5 w-5" />} tone="warn" label="Ketma-ket kun" value={s?.streak} />
        <StatCard
          icon={<Target className="h-5 w-5" />}
          tone="good"
          label="Bugungi reja"
          value={lessons.length ? `${doneToday}/${lessons.length}` : "—"}
        />
        <div className="card col-span-2 p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted">Unvon</div>
              <div className="font-bold">{rank?.name}</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-extrabold text-accent">{user?.xp}</div>
              <div className="text-[11px] text-muted">XP · {user?.level_name}</div>
            </div>
          </div>
          {rank?.next_xp ? (
            <>
              <ProgressBar className="mt-3" value={rank.xp - rank.floor} max={rank.next_xp - rank.floor} />
              <div className="mt-1 text-[11px] text-muted">
                «{rank.next_name}» gacha {rank.next_xp - rank.xp} XP
              </div>
            </>
          ) : (
            <div className="mt-3 text-xs text-muted">Eng yuqori unvon! 🏆</div>
          )}
        </div>
      </section>

      {/* Takrorlash */}
      {today.data?.reviews.length ? (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <Brain className="h-5 w-5 text-accent" /> Takrorlash vaqti
          </h2>
          {today.data.reviews.map((r) => (
            <ReviewCard key={r.id} review={r} onDone={() => qc.invalidateQueries({ queryKey: ["stats"] })} />
          ))}
        </section>
      ) : null}

      {/* Bugungi darslar */}
      <section>
        <div className="mb-3 flex items-end justify-between">
          <div>
            <h2 className="text-lg font-bold">{today.data?.from_daily ? "Bugungi darslar" : "Siz uchun tanlangan darslar"}</h2>
            <p className="text-xs text-muted">
              Har kuni soat {meta?.daily_hour ?? 8}:00 da yangilanadi · muhimlik va darajangizga qarab saralangan
            </p>
          </div>
          <Link to="/lessons" className="hidden text-sm font-semibold text-accent sm:block">
            Barcha darslar →
          </Link>
        </div>

        {today.isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        ) : today.error ? (
          <ErrorBox error={today.error} retry={() => today.refetch()} />
        ) : lessons.length ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {lessons.map((l, i) => (
              <LessonCard key={l.id} lesson={l} index={i} />
            ))}
          </div>
        ) : (
          <Empty
            icon={<Library className="h-10 w-10" />}
            title="Hozircha yangi dars yo'q"
            text="Pastdagi tugma orqali siz uchun maxsus dars tayyorlab beraman."
          />
        )}

        <div className="card mt-4 flex flex-col items-center gap-3 p-5 text-center sm:flex-row sm:text-left">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent/10 text-accent">
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="flex-1">
            <h3 className="font-bold">Vaqtingiz ko'pmi?</h3>
            <p className="text-sm text-muted">
              Yana darslar oling. Tayyorlari tugasa — AI darajangizga mos yangi dars yozib beradi.
            </p>
          </div>
          <button className="btn-primary w-full sm:w-auto" onClick={more} disabled={loadingMore}>
            {loadingMore ? <Spinner className="h-4 w-4 text-accent-ink" /> : <Library className="h-4 w-4" />}
            {loadingMore ? "Tayyorlanmoqda..." : "Yana dars yuborish"}
          </button>
        </div>
        {loadingMore && (
          <p className="mt-2 text-center text-xs text-muted">Yangi dars yozilayotgan bo'lsa, bu 30–60 soniya olishi mumkin.</p>
        )}
      </section>

      {/* Telegram ulash */}
      {user && !user.telegram_id && meta?.bot_username && <ConnectTelegram />}
    </div>
  );
}

function StatCard({ icon, label, value, tone }: { icon: ReactNode; label: string; value: ReactNode; tone: "warn" | "good" }) {
  return (
    <div className="card p-4">
      <span className={clsx("inline-flex rounded-xl p-2", tone === "warn" ? "bg-warn/10 text-warn" : "bg-good/10 text-good")}>
        {icon}
      </span>
      <div className="mt-2 text-2xl font-extrabold">{value ?? "—"}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function ReviewCard({ review, onDone }: { review: Review; onDone: () => void }) {
  const [res, setRes] = useState<{ correct: boolean; answer: number; explain: string; xp: number } | null>(null);
  const [given, setGiven] = useState<number | null>(null);
  const toast = useToast();

  async function answer(i: number) {
    if (res) return;
    setGiven(i);
    try {
      const r = await post<{ correct: boolean; answer: number; explain: string; xp: number }>(`/reviews/${review.id}`, {
        answer: i,
      });
      setRes(r);
      haptic(r.correct ? "success" : "error");
      onDone();
    } catch (e) {
      toast(errText(e), "error");
      setGiven(null);
    }
  }

  return (
    <div className="card p-4">
      <p className="text-xs text-muted">
        <Link to={`/lessons/${review.lesson.slug}`} className="font-semibold text-accent">
          {review.lesson.title}
        </Link>{" "}
        darsidan
      </p>
      <p className="mt-1 font-semibold">{review.question}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {review.options.map((o, i) => (
          <button
            key={i}
            onClick={() => answer(i)}
            disabled={!!res}
            className={clsx(
              "flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition",
              res && i === res.answer
                ? "border-good bg-good/10 text-good"
                : res && i === given
                  ? "border-bad bg-bad/10 text-bad"
                  : given === i
                    ? "border-accent"
                    : "border-line hover:border-accent",
            )}
          >
            {res && i === res.answer && <Check className="h-4 w-4" />}
            {res && i === given && i !== res.answer && <X className="h-4 w-4" />}
            {o}
          </button>
        ))}
      </div>
      {res && (
        <p className="mt-3 text-sm text-muted">
          {res.correct ? `To'g'ri! +${res.xp} XP. ` : "Ertaga yana so'rayman. "}
          {res.explain}
        </p>
      )}
    </div>
  );
}

function ConnectTelegram() {
  const toast = useToast();
  async function connect() {
    try {
      const { url } = await post<{ url: string }>("/me/telegram-link");
      window.open(url, "_blank", "noopener");
    } catch (e) {
      toast(errText(e), "error");
    }
  }
  return (
    <div className="card flex flex-col items-center gap-3 border-accent/30 bg-accent/5 p-5 text-center sm:flex-row sm:text-left">
      <Send className="h-8 w-8 text-accent" />
      <div className="flex-1">
        <h3 className="font-bold">Telegram botni ulang</h3>
        <p className="text-sm text-muted">Har kuni ertalab darslar va takrorlash savollari to'g'ridan-to'g'ri Telegramga keladi.</p>
      </div>
      <button className="btn-primary" onClick={connect}>
        Ulash
      </button>
    </div>
  );
}
