import { useQuery } from "@tanstack/react-query";
import { AppShell } from "./components/layout/app-shell";
import { QueryWorkbench } from "./features/query/query-workbench";
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
          Query, plan, execute, inspect.
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
  const datasetsQuery = useQuery({
    queryKey: ["catalog-datasets"],
    queryFn: () => apiGet<CatalogDatasetsResponse>("/catalog/datasets"),
  });

  const datasets = datasetsQuery.data?.datasets ?? [];

  return (
    <div className="flex flex-col gap-3 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm font-medium text-white">Phase F2</p>
        <p className="text-xs text-slate-400">
          Query workbench MVP
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
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

export default function App() {
  return (
    <AppShell sidebar={<Sidebar />} header={<Header />}>
      <QueryWorkbench />
    </AppShell>
  );
}