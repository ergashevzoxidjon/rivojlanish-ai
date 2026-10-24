import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { useState } from "react";
import { useAuth } from "../lib/auth";
import type { User } from "../lib/types";
import { Spinner, errText } from "./ui";

export default function GoogleButton({ linkToken, onDone }: { linkToken?: string | null; onDone?: (u: User) => void }) {
  const { meta, loginWithGoogle } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!meta) return <Spinner />;
  if (!meta.google_client_id)
    return <p className="text-sm text-bad">Google orqali kirish hali sozlanmagan (GOOGLE_CLIENT_ID).</p>;

  return (
    <GoogleOAuthProvider clientId={meta.google_client_id}>
      <div className="flex flex-col items-center gap-2">
        {busy ? (
          <Spinner className="h-6 w-6" />
        ) : (
          <GoogleLogin
            text="continue_with"
            shape="pill"
            size="large"
            locale="uz"
            onSuccess={async (res) => {
              if (!res.credential) return;
              setBusy(true);
              setError(null);
              try {
                const u = await loginWithGoogle(res.credential, linkToken);
                onDone?.(u);
              } catch (e) {
                setError(errText(e));
              } finally {
                setBusy(false);
              }
            }}
            onError={() => setError("Google bilan kirib bo'lmadi. Qayta urinib ko'ring.")}
          />
        )}
        {error && <p className="text-sm text-bad">{error}</p>}
      </div>
    </GoogleOAuthProvider>
  );
}
