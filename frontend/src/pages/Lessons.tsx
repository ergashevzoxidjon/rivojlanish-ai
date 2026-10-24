import clsx from "clsx";
import { useEffect, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Search, SearchX } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import LessonCard from "../components/LessonCard";
import { Empty, ErrorBox, PageHeader, Skeleton, Spinner } from "../components/ui";
import { get, qs } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Lesson, Paged } from "../lib/types";

const STATES = [
  { key: "", label: "Hammasi" },
  { key: "todo", label: "Bajarilmagan" },
  { key: "done", label: "Bajarilgan" },
];

export default function Lessons() {
  const { meta } = useAuth();
  const [params, setParams] = useSearchParams();
  const topic = params.get("topic") ?? "";
  const level = params.get("level") ?? "";
  const tool = params.get("tool") ?? "";
  const state = params.get("state") ?? "";
  const [q, setQ] = useState(params.get("q") ?? "");
  const [debounced, setDebounced] = useState(q);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 350);
    return () => clearTimeout(t);
  }, [q]);

  function set(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const tools = useQuery({ queryKey: ["tools"], queryFn: () => get<{ tool: string; count: number }[]>("/tools") });

  const list = useInfiniteQuery({
    queryKey: ["lessons", topic, level, tool, state, debounced],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      get<Paged<Lesson>>(`/lessons${qs({ topic, level, tool, state, q: debounced, page: pageParam, size: 12 })}`),
    getNextPageParam: (last, all) => (all.length * 12 < last.total ? all.length + 1 : undefined),
  });

  const items = list.data?.pages.flatMap((p) => p.items) ?? [];
  const total = list.data?.pages[0]?.total ?? 0;

  return (
    <div>
      <PageHeader title="Darslar" subtitle={list.data ? `${total} ta dars` : "Barcha yo'riqnomalar arxivi"} />

      <div className="card mb-5 space-y-3 p-3 sm:p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="input pl-9"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Qidirish: Claude Projects, MCP, Cursor..."
          />
        </div>
        <div className="scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1">
          <button className={clsx("chip shrink-0", !topic && "chip-on")} onClick={() => set("topic", "")}>
            Barcha mavzular
          </button>
          {meta?.topics.map((t) => (
            <button key={t.key} className={clsx("chip shrink-0", topic === t.key && "chip-on")} onClick={() => set("topic", t.key)}>
              {t.name}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
          <select className="input sm:w-44" value={level} onChange={(e) => set("level", e.target.value)} aria-label="Daraja">
            <option value="">Barcha darajalar</option>
            {meta?.levels.map((l) => (
              <option key={l.key} value={l.key}>
                {l.name}
              </option>
            ))}
          </select>
          <select className="input sm:w-44" value={tool} onChange={(e) => set("tool", e.target.value)} aria-label="Vosita">
            <option value="">Barcha vositalar</option>
            {tools.data?.map((t) => (
              <option key={t.tool} value={t.tool}>
                {t.tool} ({t.count})
              </option>
            ))}
          </select>
          <div className="col-span-2 flex rounded-xl border border-line bg-elevated p-1 sm:ml-auto">
            {STATES.map((s) => (
              <button
                key={s.key}
                onClick={() => set("state", s.key)}
                className={clsx(
                  "flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition",
                  state === s.key ? "bg-surface text-ink shadow-sm" : "text-muted",
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {list.isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : list.error ? (
        <ErrorBox error={list.error} retry={() => list.refetch()} />
      ) : items.length === 0 ? (
        <Empty icon={<SearchX className="h-10 w-10" />} title="Hech narsa topilmadi" text="Filtrlarni o'zgartirib ko'ring." />
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {items.map((l, i) => (
              <LessonCard key={l.id} lesson={l} index={i % 12} />
            ))}
          </div>
          {list.hasNextPage && (
            <div className="mt-6 flex justify-center">
              <button className="btn-ghost" onClick={() => list.fetchNextPage()} disabled={list.isFetchingNextPage}>
                {list.isFetchingNextPage ? <Spinner className="h-4 w-4" /> : null} Yana ko'rsatish
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
