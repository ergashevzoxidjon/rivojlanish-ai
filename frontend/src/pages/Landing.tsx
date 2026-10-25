import { BellRing, Brain, ClipboardCheck, GraduationCap, Send, Sparkles, Trophy } from "lucide-react";
import GoogleButton from "../components/GoogleButton";
import { Logo } from "../components/Layout";
import { useAuth } from "../lib/auth";

const FEATURES = [
  { icon: BellRing, title: "Har kuni ertalab", text: "Soat 8:00 da 1–3 ta eng muhim yangi funksiya bo'yicha dars." },
  { icon: ClipboardCheck, title: "Amaliy topshiriq + test", text: "O'qish bilan cheklanmaysiz: bajarasiz va bilimingizni tekshirasiz." },
  { icon: GraduationCap, title: "AI ustoz", text: "Tushunmagan joyingizni so'rang — o'zbek tilida tushuntirib beradi." },
  { icon: Brain, title: "Aqlli takrorlash", text: "O'tilgan darslar 3 va 7 kundan keyin qisqa savol bilan mustahkamlanadi." },
  { icon: Sparkles, title: "Darajangizga mos", text: "Test natijalariga qarab darslar qiyinligi o'zi moslashadi." },
  { icon: Trophy, title: "XP va yutuqlar", text: "Ketma-ket kunlar, unvonlar, reyting — o'rganish odatga aylanadi." },
];

export default function Landing() {
  const { meta } = useAuth();
  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Logo />
        {meta?.bot_username && (
          <a className="btn-ghost" href={`https://t.me/${meta.bot_username}`} target="_blank" rel="noreferrer">
            <Send className="h-4 w-4" /> Telegram bot
          </a>
        )}
      </header>

      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(60%_50%_at_50%_0%,rgb(var(--accent)/0.18),transparent)]" />
        <div className="mx-auto max-w-3xl px-4 pb-14 pt-12 text-center sm:pt-20">
          <span className="badge mx-auto bg-accent/10 px-3 py-1 text-xs text-accent">
            Claude · ChatGPT · Gemini · Claude Code · Cursor · n8n · MCP
          </span>
          <h1 className="mt-5 text-4xl font-extrabold leading-[1.1] tracking-tight sm:text-6xl">
            Sun'iy intellektni <span className="bg-gradient-to-r from-accent to-[#22c1a7] bg-clip-text text-transparent">har kuni</span> o'rganing
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-muted">
            AI vositalariga har kuni yangi funksiyalar qo'shilmoqda. Rivojlanish AI ularni kuzatib, siz uchun o'zbek tilida
            qadam-baqadam yo'riqnoma, topshiriq va test tayyorlab beradi.
          </p>
          <div className="mt-8 flex flex-col items-center gap-3">
            <GoogleButton />
            <p className="text-xs text-muted">Google akkauntingiz orqali bepul ro'yxatdan o'ting</p>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-20 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <div key={f.title} className="card animate-fade-up p-5" style={{ animationDelay: `${i * 60}ms` }}>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <f.icon className="h-5 w-5" />
            </span>
            <h3 className="mt-3 font-bold">{f.title}</h3>
            <p className="mt-1 text-sm text-muted">{f.text}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-line py-6 text-center text-xs text-muted">
        © {new Date().getFullYear()} Rivojlanish AI ·{" "}
        <a href="/privacy" className="hover:text-ink">
          Maxfiylik siyosati
        </a>{" "}
        ·{" "}
        <a href="/terms" className="hover:text-ink">
          Foydalanish shartlari
        </a>
      </footer>
    </div>
  );
}
