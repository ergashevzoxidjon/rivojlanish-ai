import { useState } from "react";
import { RefreshCw, UserPlus } from "lucide-react";
import { Logo } from "../components/Layout";
import { Spinner, errText } from "../components/ui";
import { post } from "../lib/api";
import { useAuth } from "../lib/auth";
import { openExternal } from "../lib/telegram";

/** Telegram Web App ichida, lekin hali Google orqali ro'yxatdan o'tmagan foydalanuvchi */
export default function NeedRegistration() {
  const { user, refresh } = useAuth();
  const [busy, setBusy] = useState(false);
  const [opened, setOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function open() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await post<{ url: string }>("/me/register-link");
      openExternal(url);
      setOpened(true);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-5 text-center">
      <Logo />
      <h1 className="mt-8 text-2xl font-extrabold">Salom, {user?.name}! 👋</h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        Darslar, testlar va AI ustozdan foydalanish uchun Google (email) orqali bir marta ro'yxatdan o'ting.
      </p>
      <button className="btn-primary mt-6 w-full max-w-xs" onClick={open} disabled={busy}>
        {busy ? <Spinner className="h-4 w-4 text-accent-ink" /> : <UserPlus className="h-4 w-4" />}
        Google bilan ro'yxatdan o'tish
      </button>
      {opened && (
        <button className="btn-ghost mt-3 w-full max-w-xs" onClick={() => refresh()}>
          <RefreshCw className="h-4 w-4" /> Ro'yxatdan o'tdim — yangilash
        </button>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
    </div>
  );
}
