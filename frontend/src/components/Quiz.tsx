import clsx from "clsx";
import { useState } from "react";
import { Check, ClipboardCheck, RotateCcw, Sparkles, X } from "lucide-react";
import { post } from "../lib/api";
import { haptic } from "../lib/telegram";
import type { LessonFull, QuizResult } from "../lib/types";
import { Spinner, errText, useToast } from "./ui";

interface Props {
  lesson: LessonFull;
  onFinished: (r: QuizResult) => void;
}

export default function Quiz({ lesson, onFinished }: Props) {
  const quiz = lesson.quiz;
  const taken = quiz.length > 0 && quiz[0].answer !== undefined;
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(false);
  const toast = useToast();

  if (!quiz.length) return null;

  const showReview = (taken && !retry) || result;

  async function choose(i: number) {
    haptic("light");
    const next = [...answers.slice(0, step), i];
    setAnswers(next);
    if (step < quiz.length - 1) {
      setTimeout(() => setStep(step + 1), 180);
      return;
    }
    setBusy(true);
    try {
      const r = await post<QuizResult>(`/lessons/${lesson.id}/quiz`, { answers: next });
      setResult(r);
      haptic(r.score === r.total ? "success" : "light");
      onFinished(r);
      if (r.level_changed) toast(`Darajangiz yangilandi! 🎚`, "info");
    } catch (e) {
      toast(errText(e), "error");
    } finally {
      setBusy(false);
    }
  }

  if (showReview) {
    const score = result ? result.score : lesson.progress.quiz_score ?? 0;
    const total = result ? result.total : lesson.progress.quiz_total ?? quiz.length;
    return (
      <div className="card p-5">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              "flex h-12 w-12 items-center justify-center rounded-2xl text-lg font-extrabold",
              score === total ? "bg-good/15 text-good" : "bg-accent/10 text-accent",
            )}
          >
            {score}/{total}
          </div>
          <div className="flex-1">
            <h3 className="font-bold">{score === total ? "Ajoyib — xatosiz!" : "Test natijasi"}</h3>
            <p className="text-sm text-muted">
              {result?.xp ? (
                <span className="inline-flex items-center gap-1 font-semibold text-accent">
                  <Sparkles className="h-4 w-4" /> +{result.xp} XP
                </span>
              ) : (
                "Javoblar va izohlar quyida"
              )}
            </p>
          </div>
          <button
            className="btn-ghost px-3"
            onClick={() => {
              setRetry(true);
              setResult(null);
              setAnswers([]);
              setStep(0);
            }}
            title="Qayta yechish (XP berilmaydi)"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
        <ol className="mt-5 space-y-4">
          {quiz.map((q, qi) => {
            const correct = result ? result.results[qi]?.answer : q.answer;
            const given = result ? result.results[qi]?.given : undefined;
            const explain = result ? result.results[qi]?.explain : q.explain;
            return (
              <li key={qi} className="text-sm">
                <p className="font-semibold">
                  {qi + 1}. {q.q}
                </p>
                <ul className="mt-2 space-y-1.5">
                  {q.options.map((o, oi) => (
                    <li
                      key={oi}
                      className={clsx(
                        "flex items-center gap-2 rounded-lg px-3 py-2",
                        oi === correct
                          ? "bg-good/10 text-good"
                          : oi === given
                            ? "bg-bad/10 text-bad"
                            : "text-muted",
                      )}
                    >
                      {oi === correct ? <Check className="h-4 w-4" /> : oi === given ? <X className="h-4 w-4" /> : <span className="w-4" />}
                      {o}
                    </li>
                  ))}
                </ul>
                {explain && <p className="mt-2 rounded-lg bg-elevated px-3 py-2 text-muted">💡 {explain}</p>}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  const q = quiz[step];
  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center gap-2">
        <ClipboardCheck className="h-5 w-5 text-accent" />
        <h3 className="font-bold">Bilimingizni tekshiring</h3>
        <div className="ml-auto flex gap-1.5">
          {quiz.map((_, i) => (
            <span
              key={i}
              className={clsx("h-1.5 w-6 rounded-full transition", i < step ? "bg-accent" : i === step ? "bg-accent/50" : "bg-line")}
            />
          ))}
        </div>
      </div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">
        Savol {step + 1} / {quiz.length}
      </p>
      <p className="mt-1 font-semibold">{q.q}</p>
      <div className="mt-4 grid gap-2">
        {q.options.map((o, i) => (
          <button
            key={i}
            disabled={busy}
            onClick={() => choose(i)}
            className={clsx(
              "rounded-xl border px-4 py-3 text-left text-sm font-medium transition hover:border-accent hover:bg-accent/5",
              answers[step] === i ? "border-accent bg-accent/10" : "border-line",
            )}
          >
            {o}
          </button>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <button className="text-muted disabled:opacity-40" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>
          ← Oldingi
        </button>
        {busy && <Spinner />}
      </div>
    </div>
  );
}
