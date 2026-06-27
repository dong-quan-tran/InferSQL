import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "./components/layout/app-shell";
import { CatalogExplorer } from "./features/catalog/catalog-explorer";
import { CopilotPanel } from "./features/copilot/copilot-panel";
import { QueryWorkbench } from "./features/query/query-workbench";
import { apiGet, API_BASE_URL, ApiError } from "./lib/api/client";
import {
  isQueryHistoryEntry,
  isSavedSnippet,
  type QueryHistoryEntry,
  type QueryHistorySource,
  type SavedSnippet,
  type SavedSnippetSnapshot,
} from "./types/history";

type CatalogDataset = {
  name: string;
  description?: string | null;
  row_count?: number | null;
};

type CatalogDatasetsResponse = {
  datasets?: CatalogDataset[];
};

type ActiveView = "query" | "catalog" | "copilot";

const STARTER_SQL = `SELECT symbol, close
FROM prices
WHERE close > 100
ORDER BY close DESC
LIMIT 10`;

const HISTORY_STORAGE_KEY = "infersql.query-history.v1";
const SNIPPETS_STORAGE_KEY = "infersql.saved-snippets.v1";

type SidebarProps = {
  activeView: ActiveView;
  onChangeView: (view: ActiveView) => void;
};

function Sidebar({ activeView, onChangeView }: SidebarProps) {
  const navItemClass = (view: ActiveView) =>
    activeView === view
      ? "rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"
      : "rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-900/40 hover:text-slate-300";

  return (
    <div className="p-5">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
          InferSQL
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Workbench</h1>
        <p className="mt-2 text-sm text-slate-400">
          Query, plan, execute, inspect, and demo.
        </p>
      </div>

      <nav className="space-y-2">
        <button
          onClick={() => onChangeView("query")}
          className={`block w-full text-left transition ${navItemClass("query")}`}
        >
          Query Workbench
        </button>

        <button
          onClick={() => onChangeView("catalog")}
          className={`block w-full text-left transition ${navItemClass("catalog")}`}
        >
          Catalog Explorer
        </button>

        <button
          onClick={() => onChangeView("copilot")}
          className={`block w-full text-left transition ${navItemClass("copilot")}`}
        >
          Copilot
        </button>

        <div className="rounded-lg px-3 py-2 text-sm text-slate-500">
          Shortcuts: g q, g c, g p
        </div>
      </nav>
    </div>
  );
}

function Header({ activeView }: { activeView: ActiveView }) {
  const datasetsQuery = useQuery({
    queryKey: ["catalog-datasets"],
    queryFn: () => apiGet<CatalogDatasetsResponse>("/catalog/datasets"),
  });

  const datasets = datasetsQuery.data?.datasets ?? [];

  return (
    <div className="flex flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm font-medium text-white">Phase F9</p>
        <p className="text-xs text-slate-400">
          {activeView === "query"
            ? "Query workbench"
            : activeView === "catalog"
              ? "Catalog explorer"
              : "Copilot"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
          API: {API_BASE_URL}
        </div>

        <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
          Datasets: {datasets.length}
        </div>

        {datasetsQuery.isError ? (
          <div className="rounded-md border border-rose-900 bg-rose-950/40 px-3 py-2 text-xs text-rose-200">
            {datasetsQuery.error instanceof ApiError
              ? datasetsQuery.error.message
              : "Catalog unavailable"}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function readStorageArray<T>(
  storage: Storage,
  key: string,
  isItem: (value: unknown) => value is T,
): T[] {
  try {
    const raw = storage.getItem(key);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isItem);
  } catch {
    return [];
  }
}

function readInitialHistory(): QueryHistoryEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  return readStorageArray(
    window.sessionStorage,
    HISTORY_STORAGE_KEY,
    isQueryHistoryEntry,
  );
}

function readInitialSnippets(): SavedSnippet[] {
  if (typeof window === "undefined") {
    return [];
  }

  return readStorageArray(
    window.localStorage,
    SNIPPETS_STORAGE_KEY,
    isSavedSnippet,
  );
}

function buildSnippetName(sql: string, count: number) {
  const firstLine = sql
    .split("\n")
    .map((line) => line.trim())
    .find(Boolean);

  if (firstLine) {
    return firstLine.slice(0, 48);
  }

  return `Snippet ${count + 1}`;
}

export default function App() {
  const [activeView, setActiveView] = useState<ActiveView>("query");
  const [sql, setSql] = useState(STARTER_SQL);
  const [history, setHistory] = useState<QueryHistoryEntry[]>(readInitialHistory);
  const [snippets, setSnippets] = useState<SavedSnippet[]>(readInitialSnippets);
  const gotoPrefixRef = useRef(false);

  useEffect(() => {
    window.sessionStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    window.localStorage.setItem(SNIPPETS_STORAGE_KEY, JSON.stringify(snippets));
  }, [snippets]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName?.toLowerCase();

      if (
        target?.isContentEditable ||
        tagName === "input" ||
        tagName === "textarea" ||
        tagName === "select"
      ) {
        return;
      }

      if (gotoPrefixRef.current) {
        if (event.key === "q") {
          event.preventDefault();
          setActiveView("query");
        } else if (event.key === "c") {
          event.preventDefault();
          setActiveView("catalog");
        } else if (event.key === "p") {
          event.preventDefault();
          setActiveView("copilot");
        }

        gotoPrefixRef.current = false;
        return;
      }

      if (event.key === "g") {
        gotoPrefixRef.current = true;
        window.setTimeout(() => {
          gotoPrefixRef.current = false;
        }, 1200);
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const favoriteCount = useMemo(
    () => history.filter((item) => item.favorite).length,
    [history],
  );

  function saveHistory(nextSql: string, source: QueryHistorySource) {
    const trimmed = nextSql.trim();
    if (!trimmed) {
      return;
    }

    setHistory((current) => {
      const existingFavorite =
        current.find((item) => item.sql === trimmed)?.favorite ?? false;

      const withoutDuplicate = current.filter((item) => item.sql !== trimmed);

      const nextEntry: QueryHistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        sql: trimmed,
        source,
        createdAt: new Date().toISOString(),
        favorite: existingFavorite,
      };

      return [nextEntry, ...withoutDuplicate].slice(0, 30);
    });
  }

  function toggleFavorite(id: string) {
    setHistory((current) =>
      current.map((item) =>
        item.id === id ? { ...item, favorite: !item.favorite } : item,
      ),
    );
  }

  function deleteHistory(id: string) {
    setHistory((current) => current.filter((item) => item.id !== id));
  }

  function clearHistory() {
    setHistory([]);
  }

  function saveSnippet(nextSql: string) {
    const trimmed = nextSql.trim();
    if (!trimmed) {
      return;
    }

    setSnippets((current) => {
      const now = new Date().toISOString();
      const existing = current.find((item) => item.sql === trimmed);

      if (existing) {
        return current.map((item) =>
          item.id === existing.id
            ? { ...item, updatedAt: now }
            : item,
        );
      }

      const nextSnippet: SavedSnippet = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: buildSnippetName(trimmed, current.length),
        sql: trimmed,
        createdAt: now,
        updatedAt: now,
        favorite: false,
      };

      return [nextSnippet, ...current];
    });
  }

  function renameSnippet(id: string, name: string) {
    const trimmed = name.trim();
    if (!trimmed) {
      return;
    }

    setSnippets((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, name: trimmed, updatedAt: new Date().toISOString() }
          : item,
      ),
    );
  }

  function toggleSnippetFavorite(id: string) {
    setSnippets((current) =>
      current.map((item) =>
        item.id === id
          ? {
            ...item,
            favorite: !item.favorite,
            updatedAt: new Date().toISOString(),
          }
          : item,
      ),
    );
  }

  function deleteSnippet(id: string) {
    setSnippets((current) => current.filter((item) => item.id !== id));
  }

  function saveSnippetSnapshot(sqlText: string, snapshot: SavedSnippetSnapshot) {
    const trimmed = sqlText.trim();
    if (!trimmed) {
      return;
    }

    setSnippets((current) =>
      current.map((item) =>
        item.sql === trimmed
          ? {
            ...item,
            updatedAt: new Date().toISOString(),
            snapshot: {
              ...item.snapshot,
              ...snapshot,
              lastRunAt: new Date().toISOString(),
            },
          }
          : item,
      ),
    );
  }

  function handleInsertSql(nextSql: string) {
    setSql(nextSql);
    setActiveView("query");
  }

  function handleCopilotSendToEditor(nextSql: string) {
    saveHistory(nextSql, "copilot");
    handleInsertSql(nextSql);
  }

  return (
    <AppShell
      sidebar={
        <Sidebar activeView={activeView} onChangeView={setActiveView} />
      }
      header={<Header activeView={activeView} />}
    >
      {activeView === "query" ? (
        <QueryWorkbench
          sql={sql}
          onSqlChange={setSql}
          history={history}
          snippets={snippets}
          onSaveHistory={saveHistory}
          onSaveSnippet={saveSnippet}
          onSaveSnippetSnapshot={saveSnippetSnapshot}
          onRenameSnippet={renameSnippet}
          onToggleSnippetFavorite={toggleSnippetFavorite}
          onDeleteSnippet={deleteSnippet}
          onToggleFavorite={toggleFavorite}
          onDeleteHistory={deleteHistory}
          onClearHistory={clearHistory}
        />
      ) : activeView === "catalog" ? (
        <CatalogExplorer onInsertSql={handleInsertSql} />
      ) : (
        <CopilotPanel onSendToEditor={handleCopilotSendToEditor} />
      )}

      <div className="sr-only" aria-live="polite">
        {favoriteCount} favorite queries saved.
      </div>
    </AppShell>
  );
}