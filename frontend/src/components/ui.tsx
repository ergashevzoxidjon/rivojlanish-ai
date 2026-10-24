import clsx from "clsx";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react";

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("animate-spin text-accent", className ?? "h-5 w-5")} aria-label="Yuklanmoqda" />;
}

export function PageLoader() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner className="h-7 w-7" />
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-xl bg-line/60", className)} />;
}

export function Empty({ icon, title, text, action }: { icon?: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center px-6 py-10 text-center">
      {icon && <div className="mb-3 text-accent">{icon}</div>}
      <h3 className="font-semibold">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBox({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Xatolik yuz berdi";
  return (
    <div className="card flex items-start gap-3 border-bad/30 p-4 text-sm">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-bad" />
      <div className="flex-1">
        <p>{msg}</p>
        {retry && (
          <button className="mt-2 font-semibold text-accent" onClick={retry}>
            Qayta urinish
          </button>
        )}
      </div>
    </div>
  );
}

export function ProgressBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className={clsx("h-2 overflow-hidden rounded-full bg-line/70", className)} role="progressbar" aria-valuenow={pct}>
      <div className="h-full rounded-full bg-accent transition-all duration-700" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={clsx("lesson-prose", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{ a: ({ ...p }) => <a {...p} target="_blank" rel="noopener noreferrer" /> }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

export function Avatar({ name, url, size = 36 }: { name: string; url?: string | null; size?: number }) {
  const initials = (name || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  if (url)
    return (
      <img src={url} alt={name} width={size} height={size} className="rounded-full object-cover" referrerPolicy="no-referrer" />
    );
  return (
    <div
      className="flex items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent"
      style={{ width: size, height: size }}
    >
      {initials}
    </div>
  );
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={clsx("relative h-6 w-11 shrink-0 rounded-full transition", checked ? "bg-accent" : "bg-line")}
    >
      <span
        className={clsx(
          "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all",
          checked ? "left-[22px]" : "left-0.5",
        )}
      />
    </button>
  );
}

/* ---------- Toast ---------- */

type ToastKind = "success" | "error" | "info";
interface ToastItem {
  id: number;
  kind: ToastKind;
  text: string;
}
const ToastContext = createContext<(text: string, kind?: ToastKind) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, kind: ToastKind = "success") => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs, { id, kind, text }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-4">
        {items.map((t) => (
          <div
            key={t.id}
            className="card pointer-events-auto flex max-w-md animate-fade-up items-center gap-2 px-4 py-3 text-sm font-medium"
          >
            {t.kind === "success" && <CheckCircle2 className="h-5 w-5 shrink-0 text-good" />}
            {t.kind === "error" && <AlertTriangle className="h-5 w-5 shrink-0 text-bad" />}
            {t.kind === "info" && <Info className="h-5 w-5 shrink-0 text-accent" />}
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

export function errText(e: unknown) {
  return e instanceof Error ? e.message : "Xatolik yuz berdi";
}
