import clsx from "clsx";
import { useEffect } from "react";
import { BarChart3, BookOpen, GraduationCap, Home, Shield, UserRound } from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { isTelegram, tg } from "../lib/telegram";
import { Avatar } from "./ui";

const NAV = [
  { to: "/", label: "Bugun", icon: Home, end: true },
  { to: "/lessons", label: "Darslar", icon: BookOpen, end: false },
  { to: "/tutor", label: "Ustoz", icon: GraduationCap, end: false },
  { to: "/progress", label: "Progress", icon: BarChart3, end: false },
];

export function Logo({ small }: { small?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2 font-extrabold tracking-tight">
      <img src="/favicon.svg" alt="" className={small ? "h-7 w-7" : "h-8 w-8"} />
      <span className={small ? "text-base" : "text-lg"}>
        Rivojlanish <span className="text-accent">AI</span>
      </span>
    </Link>
  );
}

/** Telegram ichida "Orqaga" tugmasi ichki sahifalarda ko'rinadi */
function useTelegramBackButton() {
  const loc = useLocation();
  const nav = useNavigate();
  useEffect(() => {
    if (!tg) return;
    const root = NAV.some((n) => n.to === loc.pathname);
    const back = () => nav(-1);
    if (root) tg.BackButton.hide();
    else {
      tg.BackButton.show();
      tg.BackButton.onClick(back);
    }
    return () => tg?.BackButton.offClick(back);
  }, [loc.pathname, nav]);
}

export default function Layout() {
  const { user } = useAuth();
  const loc = useLocation();
  useTelegramBackButton();
  useEffect(() => window.scrollTo(0, 0), [loc.pathname]);

  const items = user?.is_admin ? [...NAV, { to: "/admin", label: "Admin", icon: Shield, end: false }] : NAV;

  return (
    <div className="min-h-dvh">
      {!isTelegram && (
        <header className="sticky top-0 z-40 border-b border-line/70 bg-bg/80 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
            <Logo />
            <nav className="hidden flex-1 items-center gap-1 md:flex">
              {items.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    clsx(
                      "rounded-xl px-3 py-2 text-sm font-semibold transition",
                      isActive ? "bg-accent/10 text-accent" : "text-muted hover:text-ink",
                    )
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
            <Link to="/profile" className="ml-auto flex items-center gap-2 rounded-xl p-1 pr-2 hover:bg-surface md:ml-0">
              {user && <Avatar name={user.name} url={user.avatar_url} size={32} />}
              <div className="hidden text-left leading-tight sm:block">
                <div className="text-sm font-semibold">{user?.name}</div>
                <div className="text-[11px] text-muted">
                  {user?.rank.name} · {user?.xp} XP
                </div>
              </div>
            </Link>
          </div>
        </header>
      )}

      <main className={clsx("mx-auto max-w-6xl px-4 pb-28 md:pb-12", isTelegram ? "pt-4" : "pt-6")}>
        <Outlet />
      </main>

      {/* Mobil va Telegram uchun pastki menyu */}
      <nav
        className={clsx(
          "safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-line/70 bg-surface/90 backdrop-blur-xl",
          !isTelegram && "md:hidden",
        )}
      >
        <div className="mx-auto flex max-w-lg justify-around px-2 pt-1.5">
          {[...NAV, { to: "/profile", label: "Profil", icon: UserRound, end: false }].map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                clsx(
                  "flex min-w-[60px] flex-col items-center gap-0.5 rounded-xl px-2 py-1.5 text-[11px] font-semibold transition",
                  isActive ? "text-accent" : "text-muted",
                )
              }
            >
              <n.icon className="h-[22px] w-[22px]" />
              {n.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
