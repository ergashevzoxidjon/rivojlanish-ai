import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Layout";

const UPDATED = "2026-yil 25-oktabr";

function Shell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-dvh">
      <header className="mx-auto flex h-16 max-w-3xl items-center px-4">
        <Logo />
      </header>
      <main className="mx-auto max-w-3xl px-4 pb-16">
        <h1 className="text-3xl font-extrabold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-muted">Oxirgi yangilanish: {UPDATED}</p>
        <div className="lesson-prose mt-6">{children}</div>
        <div className="mt-10 flex gap-4 text-sm">
          <Link to="/" className="font-semibold text-accent">
            ← Bosh sahifa
          </Link>
          <Link to="/privacy" className="text-muted hover:text-ink">
            Maxfiylik siyosati
          </Link>
          <Link to="/terms" className="text-muted hover:text-ink">
            Foydalanish shartlari
          </Link>
        </div>
      </main>
    </div>
  );
}

export function Privacy() {
  return (
    <Shell title="Maxfiylik siyosati">
      <p>
        Rivojlanish AI (rivojlanish.mylogo.uz) — sun'iy intellekt vositalarini o'zbek tilida o'rgatuvchi platforma. Bu sahifa
        qanday ma'lumot to'planishi va qanday ishlatilishini tushuntiradi.
      </p>
      <h2>Qanday ma'lumot to'planadi</h2>
      <ul>
        <li>
          <strong>Google orqali kirishda:</strong> ismingiz, email manzilingiz va profil rasmingiz. Parolingiz bizga
          berilmaydi.
        </li>
        <li>
          <strong>Telegram orqali:</strong> Telegram ID, ism va foydalanuvchi nomi (username).
        </li>
        <li>
          <strong>O'qish faoliyati:</strong> qaysi darslar yuborilgani, o'qilgani, bajarilgani, test natijalari, XP va
          sozlamalaringiz (mavzular, kunlik darslar soni).
        </li>
        <li>
          <strong>AI ustozga savollar:</strong> siz yozgan savollar va ularga berilgan javoblar.
        </li>
      </ul>
      <h2>Ma'lumotlar nima uchun ishlatiladi</h2>
      <ul>
        <li>Akkauntingizni aniqlash va Telegram bilan bog'lash.</li>
        <li>Sizga mos darslarni tanlash, progress va statistikani ko'rsatish.</li>
        <li>Ertalabki darslar va takrorlash savollarini Telegram orqali yuborish.</li>
      </ul>
      <p>Ma'lumotlaringiz sotilmaydi va reklama uchun ishlatilmaydi.</p>
      <h2>Uchinchi tomon xizmatlari</h2>
      <ul>
        <li>
          <strong>Google</strong> — faqat kirish (ism, email, rasm) uchun.
        </li>
        <li>
          <strong>Telegram</strong> — bot orqali xabar yuborish uchun.
        </li>
        <li>
          <strong>Anthropic (Claude API)</strong> — darslar yozish va AI ustoz javoblari uchun. Ustozga yozgan savolingiz
          javob olish uchun Claude API'ga yuboriladi; ism yoki email yuborilmaydi.
        </li>
      </ul>
      <h2>Saqlash va xavfsizlik</h2>
      <p>
        Ma'lumotlar platforma serverida saqlanadi va HTTPS orqali uzatiladi. Kirish JWT sessiya tokeni bilan himoyalangan.
      </p>
      <h2>Sizning huquqlaringiz</h2>
      <p>
        Ma'lumotlaringizni ko'rish, o'zgartirish yoki akkauntingizni butunlay o'chirishni so'rashingiz mumkin. Buning uchun{" "}
        <a href="mailto:zoxidjon2607.ergashev@gmail.com">zoxidjon2607.ergashev@gmail.com</a> manziliga yozing. AI ustoz
        suhbatini istalgan vaqtda o'zingiz tozalashingiz mumkin.
      </p>
      <h2>Aloqa</h2>
      <p>
        Savollar bo'yicha: <a href="mailto:zoxidjon2607.ergashev@gmail.com">zoxidjon2607.ergashev@gmail.com</a>
      </p>
    </Shell>
  );
}

export function Terms() {
  return (
    <Shell title="Foydalanish shartlari">
      <p>Rivojlanish AI platformasidan foydalanib, siz quyidagi shartlarga rozilik bildirasiz.</p>
      <h2>Xizmat</h2>
      <p>
        Platforma sun'iy intellekt vositalari bo'yicha o'quv materiallari, topshiriqlar, testlar va AI ustoz yordamini
        taqdim etadi. Xizmat "boricha" taqdim etiladi va vaqti-vaqti bilan o'zgarishi mumkin.
      </p>
      <h2>AI tomonidan yaratilgan kontent</h2>
      <p>
        Darslar va ustoz javoblarining bir qismi sun'iy intellekt yordamida tayyorlanadi. Biz ularni aniq bo'lishiga harakat
        qilamiz, lekin xato bo'lishi mumkin. Muhim qarorlardan oldin rasmiy manbalarni tekshiring — har bir darsda manba
        havolasi berilgan.
      </p>
      <h2>Foydalanuvchi majburiyatlari</h2>
      <ul>
        <li>Platformadan qonunga zid yoki boshqalarga zarar yetkazuvchi maqsadlarda foydalanmang.</li>
        <li>AI ustozdan foydalanishda kunlik limitlarga rioya qiling, tizimni ataylab ortiqcha yuklamang.</li>
        <li>Akkauntingiz xavfsizligi uchun o'zingiz javobgarsiz.</li>
      </ul>
      <h2>Akkauntni to'xtatish</h2>
      <p>Shartlar buzilganda akkaunt cheklanishi yoki o'chirilishi mumkin. Siz ham istalgan vaqtda akkauntni o'chirishni so'rashingiz mumkin.</p>
      <h2>Aloqa</h2>
      <p>
        <a href="mailto:zoxidjon2607.ergashev@gmail.com">zoxidjon2607.ergashev@gmail.com</a>
      </p>
    </Shell>
  );
}
