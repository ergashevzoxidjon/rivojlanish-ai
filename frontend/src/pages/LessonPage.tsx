import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Circle, Clock, ExternalLink, Flame, GraduationCap, Share2, Target } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import LessonCard, { TopicIcon } from "../components/LessonCard";
import Quiz from "../components/Quiz";
import TutorChat from "../components/TutorChat";
import { ErrorBox, Markdown, PageLoader, errText, useToast } from "../components/ui";
import { get, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import { haptic, isTelegram } from "../lib/telegram";
import type { LessonFull, User } from "../lib/types";

export default function LessonPage() {
  const { slug } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const { user, setUser, meta } = useAuth();
  const key = ["lesson", slug];
  const { data: lesson, isLoading, error, refetch } = useQuery({
    queryKey: key,
    queryFn: () => get<LessonFull>(`/lessons/${slug}`),
  });
  const [showTutor, setShowTutor] = useState(false);
  const readSent = useRef(false);

  // 8 soniya o'qilgandan keyin "o'qildi" deb belgilanadi
  useEffect(() => {
    if (!lesson || lesson.progress.read || readSent.current) return;
    const t = setTimeout(async () => {
      readSent.current = true;
      try {
        const r = await post<{ xp: number }>(`/lessons/${lesson.id}/read`);
        if (user) setUser({ ...user, xp: r.xp });
        qc.invalidateQueries({ queryKey: ["stats"] });
      } catch {
        /* jim */
      }
    }, 8000);
    return () => clearTimeout(t);
  }, [lesson, user, setUser, qc]);

  async function toggleDone() {
    if (!lesson) return;
    const done = !lesson.progress.done;
    try {
      const r = await post<{ xp: number }>(`/lessons/${lesson.id}/done`, { done });
      qc.setQueryData<LessonFull>(key, { ...lesson, progress: { ...lesson.progress, done, read: true } });
      if (user) setUser({ ...user, xp: r.xp });
      qc.invalidateQueries({ queryKey: ["today"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      if (done) {
        haptic("success");
        toast("Barakalla! Topshiriq bajarildi 🎉");
      }
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  async function share() {
    if (!lesson) return;
    const url = meta?.bot_username
      ? `https://t.me/${meta.bot_username}?start=l_${lesson.id}`
      : window.location.href;
    try {
      if (navigator.share) await navigator.share({ title: lesson.title, text: lesson.summary, url });
      else {
        await navigator.clipboard.writeText(url);
        toast("Havola nusxalandi");
      }
    } catch {
      /* bekor qilindi */
    }
  }

  if (isLoading) return <PageLoader />;
  if (error || !lesson) return <ErrorBox error={error} retry={() => refetch()} />;

  const p = lesson.progress;
  return (
    <div className="mx-auto max-w-3xl">
      {!isTelegram && (
        <button onClick={() => nav(-1)} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink">
          <ArrowLeft className="h-4 w-4" /> Orqaga
        </button>
      )}

      <article className="animate-fade-up">
        <div className="flex items-center gap-2 text-xs font-semibold text-muted">
          <TopicIcon topic={lesson.topic} className="h-7 w-7 rounded-lg" />
          <span>{lesson.topic_name}</span>
          {lesson.tool && (
            <>
              <span>·</span>
              <Link to={`/lessons?tool=${encodeURIComponent(lesson.tool)}`} className="text-ink/80 hover:text-accent">
                {lesson.tool}
              </Link>
            </>
          )}
        </div>
        <h1 className="mt-3 text-2xl font-extrabold leading-tight tracking-tight sm:text-4xl">{lesson.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="badge">{lesson.level_name}</span>
          <span className="badge">
            <Clock className="h-3 w-3" /> {lesson.minutes} daqiqa
          </span>
          {lesson.importance >= 8 && (
            <span className="badge bg-warn/10 text-warn">
              <Flame className="h-3 w-3" /> Muhim yangilik
            </span>
          )}
          <button onClick={share} className="badge ml-auto hover:text-ink">
            <Share2 className="h-3 w-3" /> Ulashish
          </button>
        </div>

        <div className="card mt-5 border-accent/25 bg-accent/5 p-4 text-[15px] leading-relaxed">
          <div className="mb-1 text-xs font-bold uppercase tracking-wide text-accent">Bu nima?</div>
          {lesson.summary}
        </div>

        <Markdown className="mt-6 sm:prose-lg">{lesson.body_md}</Markdown>

        {/* Topshiriq */}
        <div className={clsx("card mt-8 p-5", p.done && "border-good/40")}>
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-accent" />
            <h2 className="font-bold">Amaliy topshiriq</h2>
          </div>
          <Markdown className="mt-2 prose-sm">{lesson.task_md}</Markdown>
          <button onClick={toggleDone} className={clsx("mt-4 w-full sm:w-auto", p.done ? "btn-soft" : "btn-primary")}>
            {p.done ? <CheckCircle2 className="h-4 w-4" /> : <Circle className="h-4 w-4" />}
            {p.done ? "Bajarildi" : "Bajardim"}
          </button>
        </div>

        {/* Test */}
        {lesson.quiz.length > 0 && (
          <div className="mt-6">
            <Quiz
              lesson={lesson}
              onFinished={(r) => {
                if (user) setUser({ ...user, xp: r.user_xp, level: r.user_level } as User);
                qc.invalidateQueries({ queryKey: ["stats"] });
              }}
            />
          </div>
        )}

        {/* AI ustoz */}
        <div className="mt-6">
          {showTutor ? (
            <TutorChat
              lessonId={lesson.id}
              compact
              suggestions={["Buni oddiyroq tushuntiring", "Amaliy misol keltiring", "Topshiriqni qanday boshlay?"]}
            />
          ) : (
            <button onClick={() => setShowTutor(true)} className="card flex w-full items-center gap-3 p-4 text-left hover:border-accent/40">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
                <GraduationCap className="h-5 w-5" />
              </span>
              <div>
                <div className="font-bold">Tushunmagan joyingiz bormi?</div>
                <div className="text-sm text-muted">AI ustozdan shu dars bo'yicha so'rang</div>
              </div>
            </button>
          )}
        </div>

        {lesson.source_url && (
          <a
            href={lesson.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-accent"
          >
            <ExternalLink className="h-4 w-4" /> Rasmiy manba
          </a>
        )}
      </article>

      {lesson.related && lesson.related.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 text-lg font-bold">O'xshash darslar</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {lesson.related.map((r) => (
              <LessonCard key={r.id} lesson={r} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
