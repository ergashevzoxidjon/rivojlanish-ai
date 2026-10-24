import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { timeAgo } from "../../components/LessonCard";
import { Avatar, ErrorBox, PageLoader, Toggle, errText, useToast } from "../../components/ui";
import { get, patch, qs } from "../../lib/api";
import type { Paged, User } from "../../lib/types";

type AdminUser = User & { created_at: string; last_active_at: string | null; bot_blocked: boolean; done: number };

export default function AdminUsers() {
  const [q, setQ] = useState("");
  const qc = useQueryClient();
  const toast = useToast();
  const users = useQuery({
    queryKey: ["admin", "users", q],
    queryFn: () => get<Paged<AdminUser>>(`/admin/users${qs({ q })}`),
  });

  async function setAdmin(u: AdminUser, v: boolean) {
    try {
      await patch(`/admin/users/${u.id}`, { is_admin: v });
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    } catch (e) {
      toast(errText(e), "error");
    }
  }

  return (
    <div className="space-y-4">
      <input className="input sm:w-80" placeholder="Ism, email yoki username" value={q} onChange={(e) => setQ(e.target.value)} />
      {users.isLoading ? (
        <PageLoader />
      ) : users.error ? (
        <ErrorBox error={users.error} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="p-3">Foydalanuvchi</th>
                <th className="p-3">Daraja / XP</th>
                <th className="p-3 text-right">Bajargan</th>
                <th className="p-3">Oxirgi faollik</th>
                <th className="p-3">Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.data?.items.map((u) => (
                <tr key={u.id}>
                  <td className="p-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar name={u.name} url={u.avatar_url} size={32} />
                      <div className="min-w-0">
                        <div className="font-semibold">{u.name}</div>
                        <div className="flex items-center gap-1.5 text-xs text-muted">
                          {u.email ?? <span className="text-warn">ro'yxatdan o'tmagan</span>}
                          {u.telegram_id && (
                            <span className={u.bot_blocked ? "text-bad" : "text-accent"} title={u.bot_blocked ? "Botni bloklagan" : "Telegram ulangan"}>
                              <Send className="inline h-3 w-3" />
                              {u.telegram_username && ` @${u.telegram_username}`}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="p-3 text-xs">
                    {u.level_name} · <b>{u.xp}</b> XP
                  </td>
                  <td className="p-3 text-right">{u.done}</td>
                  <td className="p-3 text-xs text-muted">{u.last_active_at ? timeAgo(u.last_active_at) : "—"}</td>
                  <td className="p-3">
                    <Toggle checked={u.is_admin} onChange={(v) => setAdmin(u, v)} label="Admin" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-line p-3 text-xs text-muted">Jami: {users.data?.total}</div>
        </div>
      )}
    </div>
  );
}
