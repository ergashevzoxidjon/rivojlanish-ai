import clsx from "clsx";
import { Bot, CheckCircle2, Clock, Code2, Flame, MessagesSquare, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import type { Lesson, Topic } from "../lib/types";

export const topicStyle: Record<Topic, { icon: typeof Bot; tint: string }> = {
  chat: { icon: MessagesSquare, tint: "text-[#7c6cff] bg-[#7c6cff]/10" },
  coding: { icon: Code2, tint: "text-[#0ea5a3] bg-[#0ea5a3]/10" },
  automation: { icon: Bot, tint: "text-[#e08a1e] bg-[#e08a1e]/10" },
};

export function TopicIcon({ topic, className }: { topic: Topic; className?: string }) {
  const s = topicStyle[topic] ?? topicStyle.chat;
  const Icon = s.icon;
  return (
    <span className={clsx("inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", s.tint, className)}>
      <Icon className="h-[18px] w-[18px]" />
    </span>
  );
}

export function timeAgo(iso: string | null) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.round(diff / 60))} daqiqa oldin`;
  if (diff < 86400) return `${Math.round(diff / 3600)} soat oldin`;
  if (diff < 86400 * 7) return `${Math.round(diff / 86400)} kun oldin`;
  return new Date(iso).toLocaleDateString("uz-UZ", { day: "numeric", month: "short" });
}

export default function LessonCard({ lesson, index }: { lesson: Lesson; index?: number }) {
  const p = lesson.progress;
  return (
    <Link
      to={`/lessons/${lesson.slug}`}
      className="card group flex animate-fade-up flex-col p-4 transition hover:-translate-y-0.5 hover:border-accent/40"
      style={index !== undefined ? { animationDelay: `${index * 50}ms` } : undefined}
    >
      <div className="flex items-start gap-3">
        <TopicIcon topic={lesson.topic} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-medium text-muted">
            {lesson.tool && <span className="font-semibold text-ink/80">{lesson.tool}</span>}
            <span>·</span>
            <span>{lesson.level_name}</span>
            {lesson.importance >= 8 && (
              <span className="badge bg-warn/10 text-warn">
                <Flame className="h-3 w-3" /> Muhim
              </span>
            )}
            {lesson.origin === "on_demand" && (
              <span className="badge">
                <Sparkles className="h-3 w-3" /> Siz uchun
              </span>
            )}
          </div>
          <h3 className="mt-1 font-semibold leading-snug group-hover:text-accent">{lesson.title}</h3>
        </div>
        {p.done && <CheckCircle2 className="h-5 w-5 shrink-0 text-good" aria-label="Bajarilgan" />}
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-muted">{lesson.summary}</p>
      <div className="mt-3 flex items-center gap-3 text-xs text-muted">
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" /> {lesson.minutes} daq
        </span>
        {p.quiz_total ? (
          <span>
            Test: {p.quiz_score}/{p.quiz_total}
          </span>
        ) : lesson.quiz_count ? (
          <span>{lesson.quiz_count} savolli test</span>
        ) : null}
        <span className="ml-auto">{timeAgo(lesson.published_at)}</span>
      </div>
    </Link>
  );
}
