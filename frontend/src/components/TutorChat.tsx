import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { GraduationCap, SendHorizontal, Trash2 } from "lucide-react";
import { del, get, post } from "../lib/api";
import type { ChatMessage } from "../lib/types";
import { Markdown, Spinner, errText, useToast } from "./ui";

interface Props {
  /** Dars ichida bo'lsa uning id si; umumiy ustoz uchun undefined */
  lessonId?: number;
  suggestions?: string[];
  className?: string;
  compact?: boolean;
}

export default function TutorChat({ lessonId, suggestions = [], className, compact }: Props) {
  const base = lessonId ? `/lessons/${lessonId}/chat` : "/tutor";
  const askUrl = lessonId ? `/lessons/${lessonId}/ask` : "/tutor";
  const key = ["chat", lessonId ?? "general"];
  const qc = useQueryClient();
  const toast = useToast();
  const { data: history = [], isLoading } = useQuery({ queryKey: key, queryFn: () => get<ChatMessage[]>(base) });
  const [pending, setPending] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [left, setLeft] = useState<number | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [history.length, pending]);

  async function send(q: string) {
    const question = q.trim();
    if (!question || pending) return;
    setText("");
    setPending(question);
    try {
      const r = await post<{ answer: string; left: number }>(askUrl, { question });
      setLeft(r.left);
      await qc.invalidateQueries({ queryKey: key });
    } catch (e) {
      toast(errText(e), "error");
      setText(question);
    } finally {
      setPending(null);
    }
  }

  async function clear() {
    await del(base);
    qc.setQueryData(key, []);
  }

  const empty = !isLoading && history.length === 0 && !pending;

  return (
    <div className={clsx("card flex flex-col overflow-hidden", className)}>
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent/10 text-accent">
          <GraduationCap className="h-[18px] w-[18px]" />
        </span>
        <div className="flex-1 leading-tight">
          <div className="text-sm font-bold">AI ustoz</div>
          <div className="text-[11px] text-muted">
            {lessonId ? "Shu dars bo'yicha savol bering" : "AI vositalari haqida istalgan savol"}
            {left !== null && ` · bugun yana ${left} ta savol`}
          </div>
        </div>
        {history.length > 0 && (
          <button onClick={clear} className="rounded-lg p-2 text-muted hover:bg-elevated hover:text-ink" title="Suhbatni tozalash">
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className={clsx("flex-1 space-y-3 overflow-y-auto px-4 py-4", compact ? "max-h-[420px]" : "min-h-[50vh]")}>
        {isLoading && <Spinner />}
        {empty && (
          <div className="py-6 text-center text-sm text-muted">
            <p>Savolingizni yozing — o'zbek tilida tushuntirib beraman.</p>
            {suggestions.length > 0 && (
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {history.map((m) => (
          <Bubble key={m.id} role={m.role} content={m.content} />
        ))}
        {pending && (
          <>
            <Bubble role="user" content={pending} />
            <div className="flex items-center gap-2 text-sm text-muted">
              <Spinner className="h-4 w-4" /> Ustoz o'ylamoqda...
            </div>
          </>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="flex items-end gap-2 border-t border-line p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(text);
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(text);
            }
          }}
          rows={1}
          maxLength={2000}
          placeholder="Savolingiz..."
          className="input max-h-32 min-h-[44px] resize-none"
        />
        <button className="btn-primary h-11 w-11 shrink-0 p-0" disabled={!text.trim() || !!pending} aria-label="Yuborish">
          <SendHorizontal className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
}

function Bubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  if (role === "user")
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-sm text-accent-ink">
          {content}
        </div>
      </div>
    );
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-md bg-elevated px-4 py-3 text-sm">
      <Markdown className="prose-sm [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">{content}</Markdown>
    </div>
  );
}
