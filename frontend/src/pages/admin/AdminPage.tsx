import clsx from "clsx";
import { useState } from "react";
import { PageHeader } from "../../components/ui";
import AdminLessons from "./AdminLessons";
import AdminOverview from "./AdminOverview";
import AdminSources from "./AdminSources";
import AdminUsers from "./AdminUsers";

const TABS = [
  { key: "overview", label: "Umumiy" },
  { key: "lessons", label: "Darslar" },
  { key: "sources", label: "Manbalar" },
  { key: "users", label: "Foydalanuvchilar" },
] as const;

type Tab = (typeof TABS)[number]["key"];

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>(() => {
    try {
      return (sessionStorage.getItem("admin_tab") as Tab) || "overview";
    } catch {
      return "overview";
    }
  });

  function choose(t: Tab) {
    setTab(t);
    try {
      sessionStorage.setItem("admin_tab", t);
    } catch {
      /* e'tiborsiz */
    }
  }

  return (
    <div>
      <PageHeader title="Admin panel" subtitle="Kontent, manbalar va foydalanuvchilarni boshqarish" />
      <div className="scrollbar-none -mx-1 mb-5 flex gap-1 overflow-x-auto px-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => choose(t.key)}
            className={clsx(
              "shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition",
              tab === t.key ? "bg-accent text-accent-ink" : "text-muted hover:bg-surface hover:text-ink",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "overview" && <AdminOverview />}
      {tab === "lessons" && <AdminLessons />}
      {tab === "sources" && <AdminSources />}
      {tab === "users" && <AdminUsers />}
    </div>
  );
}
