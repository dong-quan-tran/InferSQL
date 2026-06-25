import { useQuery } from "@tanstack/react-query";
import { AppShell } from "./components/layout/app-shell";
import { apiGet, API_BASE_URL, ApiError } from "./lib/api/client";

type CatalogDataset = {
  name: string;
  description?: string | null;
  row_count?: number | null;
};

type CatalogDatasetsResponse = {
  datasets?: CatalogDataset[];
};

function Sidebar() {
  return (
    <div className="p-5">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
          InferSQL
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Workbench</h1>
        <p className="mt-2 text-sm text-slate-400">
          Frontend scaffold for query, catalog, and copilot flows.
        </p>
      </div>

      <nav className="space-y-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200">
          Query Workbench
        </div>
        <div className="rounded-lg px-3 py-2 text-sm text-slate-500">
          Catalog Explorer
        </div>
        <div className="rounded-lg px-3 py-2 text-sm text-slate-500">
          Copilot
        </div>
        <div className="rounded-lg px-3 py-2 text-sm text-slate-500">
          Settings
        </div>
      </nav>
    </div>
  );
}

function Header() {
  return (
    <div className="flex items-center justify-between px-6 py-4">
      <div>
        <p className="text-sm font-medium text-white">Phase F1</p>
        <p className="text-xs text-slate-400">
          App shell, query client, API wiring
        </p>
      </div>

      <div className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
        {API_BASE_URL}
      </div>
    </div>
  );
}

export default function App() {
  const datasetsQuery = useQuery({
    queryKey: ["catalog-datasets"],
    queryFn: () => apiGet<CatalogDatasetsResponse>("/catalog/datasets"),
  });

  const datasets = datasetsQuery.data?.datasets ?? [];

  return (
    <AppShell sidebar={<Sidebar />} header={<Header />}>
      <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">
              Frontend status
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              This page confirms the frontend scaffold is running and can talk
              to the backend catalog API.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                App
              </p>
              <p className="mt-2 text-sm text-slate-200">
                React + Vite + TypeScript
              </p>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                State
              </p>
              <p className="mt-2 text-sm text-slate-200">TanStack Query</p>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Backend
              </p>
              <p className="mt-2 text-sm text-slate-200">Catalog API wired</p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-white">Catalog check</h2>
            <p className="mt-1 text-sm text-slate-400">
              Live request to <code>/catalog/datasets</code>
            </p>
          </div>

          {datasetsQuery.isLoading ? (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
              Loading datasets…
            </div>
          ) : datasetsQuery.isError ? (
            <div className="rounded-lg border border-rose-900 bg-rose-950/40 p-4 text-sm text-rose-200">
              <p className="font-medium">Failed to load catalog datasets.</p>
              <p className="mt-2 break-words text-rose-300">
                {datasetsQuery.error instanceof ApiError
                  ? datasetsQuery.error.message
                  : "Unknown error"}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  Dataset count
                </p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {datasets.length}
                </p>
              </div>

              <div className="space-y-2">
                {datasets.length === 0 ? (
                  <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                    No datasets returned yet.
                  </div>
                ) : (
                  datasets.map((dataset: CatalogDataset) => (
                    <div
                      key={dataset.name}
                      className="rounded-lg border border-slate-800 bg-slate-950 p-4"
                    >
                      <p className="font-medium text-white">{dataset.name}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        {dataset.description || "No description"}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        Rows: {dataset.row_count ?? "unknown"}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}