import { useState } from "react";
import { CheckCircle2, Send } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import GoogleButton from "../components/GoogleButton";
import { Logo } from "../components/Layout";
import { useAuth } from "../lib/auth";
import type { User } from "../lib/types";

/** Botdan kelgan havola: /register?t=TOKEN — Google bilan kirib, Telegram akkauntni bog'laydi */
export default function Register() {
  const [params] = useSearchParams();
  const token = params.get("t");
  const { meta } = useAuth();
  const [done, setDone] = useState<User | null>(null);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="mb-6">
        <Logo />
      </div>
      <div className="card w-full max-w-md p-7 text-center">
        {done ? (
          <>
            <CheckCircle2 className="mx-auto h-14 w-14 text-good" />
            <h1 className="mt-3 text-xl font-extrabold">Ro'yxatdan o'tdingiz!</h1>
            <p className="mt-2 text-sm text-muted">
              {done.telegram_id
                ? "Telegram akkauntingiz ham ulandi. Endi botga qayting — har kuni ertalab darslar keladi."
                : "Endi platformadan foydalanishingiz mumkin."}
            </p>
            <div className="mt-6 flex flex-col gap-2">
              {meta?.bot_username && (
                <a className="btn-primary" href={`https://t.me/${meta.bot_username}?start=ok`}>
                  <Send className="h-4 w-4" /> Telegram botga qaytish
                </a>
              )}
              <Link to="/" className="btn-ghost">
                Saytda davom etish
              </Link>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-xl font-extrabold">Ro'yxatdan o'tish</h1>
            <p className="mt-2 text-sm text-muted">
              Google (email) akkauntingiz bilan kiring.
              {token && " Telegram akkauntingiz avtomatik ulanadi."}
            </p>
            <div className="mt-6">
              <GoogleButton linkToken={token} onDone={setDone} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
