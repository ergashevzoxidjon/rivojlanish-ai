import clsx from "clsx";
import { useState } from "react";
import { CheckCircle2, LogOut, Moon, Send, Shield, Sun } from "lucide-react";
import { Link } from "react-router-dom";
import { Avatar, PageHeader, Toggle, errText, useToast } from "../components/ui";
import { patch, post } from "../lib/api";
import { useAuth } from "../lib/auth";
import { isTelegram } from "../lib/telegram";
import type { Topic, User } from "../lib/types";

function useTheme() {
  const read = () => {
    try {
      return localStorage.getItem("theme") ?? "system";
    } catch {
      return "system";
    }
  };
  const [theme, setThemeState] = useState(read);
  function setTheme(t: string) {
    setThemeState(t);
    try {
      localStorage.setItem("theme", t);
    } catch {
      /* e'tiborsiz */
    }
    applyTheme(t);
  }
  return [theme, setTheme] as const;
}

export function applyTheme(t: string | null) {
  if (isTelegram) return;
  const root = document.documentElement;
  root.classList.toggle("dark", t === "dark");
  root.classList.toggle("light", t === "light");
}

export default function Profile() {
  const { user, meta, setUser, logout } = useAuth();
  const toast = useToast();
  const [theme, setTheme] = useTheme();
  if (!user || !meta) return null;

  async function save(body: Partial<Pick<User, "topics" | "daily_count" | "notify">>) {
    try {
      setUser(await patch<User>("/me", body));
      toast("Saqlandi");
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  function toggleTopic(t: Topic) {
    const has = user!.topics.includes(t);
    if (has && user!.topics.length === 1) return toast("Kamida bitta mavzu bo'lishi kerak", "info");
    save({ topics: has ? user!.topics.filter((x) => x !== t) : [...user!.topics, t] });
  }

  async function connectTelegram() {
    try {
      const { url } = await post<{ url: string }>("/me/telegram-link");
      window.open(url, "_blank", "noopener");
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  const counts = Array.from({ length: meta.daily_max - meta.daily_min + 1 }, (_, i) => meta.daily_min + i);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <PageHeader title="Profil" />

      <div className="card flex items-center gap-4 p-5">
        <Avatar name={user.name} url={user.avatar_url} size={56} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-lg font-bold">{user.name}</div>
          <div className="truncate text-sm text-muted">{user.email}</div>
          <div className="mt-1 text-xs font-semibold text-accent">
            {user.rank.name} · {user.xp} XP · {user.level_name}
          </div>
        </div>
      </div>

      <section className="card p-5">
        <h2 className="font-bold">Mavzular</h2>
        <p className="text-xs text-muted">Darslar faqat tanlangan mavzulardan keladi</p>
        <div className="mt-3 grid gap-2">
          {meta.topics.map((t) => {
            const on = user.topics.includes(t.key);
            return (
              <button
                key={t.key}
                onClick={() => toggleTopic(t.key)}
                className={clsx(
                  "flex items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-medium transition",
                  on ? "border-accent bg-accent/5" : "border-line",
                )}
              >
                {t.name}
                <CheckCircle2 className={clsx("h-5 w-5", on ? "text-accent" : "text-line")} />
              </button>
            );
          })}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="font-bold">Kunlik darslar</h2>
        <p className="text-xs text-muted">Har kuni soat {meta.daily_hour}:00 da Telegramga nechta dars kelsin</p>
        <div className="mt-3 flex rounded-xl border border-line bg-elevated p-1">
          {counts.map((n) => (
            <button
              key={n}
              onClick={() => save({ daily_count: n })}
              className={clsx(
                "flex-1 rounded-lg py-2 text-sm font-semibold transition",
                user.daily_count === n ? "bg-surface text-ink shadow-sm" : "text-muted",
              )}
            >
              {n} ta
            </button>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Ertalabki xabar</div>
            <div className="text-xs text-muted">O'chirsangiz, darslarni faqat o'zingiz so'raganda olasiz</div>
          </div>
          <Toggle checked={user.notify} onChange={(v) => save({ notify: v })} label="Ertalabki xabar" />
        </div>
      </section>

      <section className="card p-5">
        <h2 className="font-bold">Telegram</h2>
        {user.telegram_id ? (
          <p className="mt-1 flex items-center gap-2 text-sm text-good">
            <CheckCircle2 className="h-4 w-4" /> Ulangan {user.telegram_username && `(@${user.telegram_username})`}
          </p>
        ) : (
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="text-sm text-muted">Darslar va eslatmalar Telegramga kelishi uchun botni ulang.</p>
            <button className="btn-primary shrink-0" onClick={connectTelegram}>
              <Send className="h-4 w-4" /> Ulash
            </button>
          </div>
        )}
      </section>

      {!isTelegram && (
        <section className="card p-5">
          <h2 className="font-bold">Ko'rinish</h2>
          <div className="mt-3 flex rounded-xl border border-line bg-elevated p-1">
            {[
              { k: "light", label: "Yorug'", icon: Sun },
              { k: "system", label: "Tizim", icon: null },
              { k: "dark", label: "Qorong'i", icon: Moon },
            ].map((o) => (
              <button
                key={o.k}
                onClick={() => setTheme(o.k)}
                className={clsx(
                  "flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-semibold transition",
                  theme === o.k ? "bg-surface text-ink shadow-sm" : "text-muted",
                )}
              >
                {o.icon && <o.icon className="h-4 w-4" />} {o.label}
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        {user.is_admin && (
          <Link to="/admin" className="btn-ghost flex-1">
            <Shield className="h-4 w-4" /> Admin panel
          </Link>
        )}
        {!isTelegram && (
          <button className="btn-ghost flex-1 text-bad" onClick={logout}>
            <LogOut className="h-4 w-4" /> Chiqish
          </button>
        )}
      </div>
    </div>
  );
}
