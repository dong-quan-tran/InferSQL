import { useEffect, useState } from "react";

type BenchmarkRow = Record<string, unknown>;

type BenchmarkArtifact =
    | {
        benchmarks?: BenchmarkRow[];
        rows?: BenchmarkRow[];
        summary?: BenchmarkRow[];
        cases?: BenchmarkRow[];
    }
    | BenchmarkRow[];

const DEFAULT_BENCHMARK_URL = "/benchmarks/summary.json";

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function extractRows(data: BenchmarkArtifact | null): BenchmarkRow[] {
    if (!data) {
        return [];
    }

    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data.benchmarks)) {
        return data.benchmarks;
    }

    if (Array.isArray(data.rows)) {
        return data.rows;
    }

    if (Array.isArray(data.summary)) {
        return data.summary;
    }

    if (Array.isArray(data.cases)) {
        return data.cases;
    }

    return [];
}

function inferColumns(rows: BenchmarkRow[]): string[] {
    const columnSet = new Set<string>();

    for (const row of rows) {
        Object.keys(row).forEach((key) => columnSet.add(key));
    }

    return Array.from(columnSet);
}

function formatCell(value: unknown): string {
    if (value === null || value === undefined) return "null";
    if (typeof value === "number") return value.toString();
    if (typeof value === "string") return value;
    if (typeof value === "boolean") return value ? "true" : "false";
    return JSON.stringify(value);
}

export function BenchmarkViewer() {
    const [artifact, setArtifact] = useState<BenchmarkArtifact | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;

        async function loadArtifact() {
            setIsLoading(true);
            setError(null);

            try {
                const response = await fetch(DEFAULT_BENCHMARK_URL, {
                    headers: {
                        Accept: "application/json",
                    },
                });

                if (!response.ok) {
                    throw new Error(`Artifact unavailable (${response.status})`);
                }

                const payload = await response.json();

                if (!isMounted) {
                    return;
                }

                if (!Array.isArray(payload) && !isObject(payload)) {
                    throw new Error("Unsupported benchmark artifact format.");
                }

                setArtifact(payload as BenchmarkArtifact);
            } catch (err) {
                if (!isMounted) {
                    return;
                }

                setError(err instanceof Error ? err.message : "Failed to load benchmark artifact.");
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        }

        loadArtifact();

        return () => {
            isMounted = false;
        };
    }, []);

    const rows = extractRows(artifact);
    const columns = inferColumns(rows);

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Benchmarks</h2>
                <p className="mt-1 text-sm text-slate-400">
                    View Phase 12 benchmark artifacts when available.
                </p>
            </div>

            {isLoading ? (
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                    Loading benchmark artifact...
                </div>
            ) : error ? (
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                    {error}
                </div>
            ) : !rows.length ? (
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                    No benchmark rows available yet.
                </div>
            ) : (
                <div className="space-y-3">
                    <div className="text-xs text-slate-500">
                        {rows.length} row{rows.length === 1 ? "" : "s"} loaded from{" "}
                        <span className="text-slate-400">{DEFAULT_BENCHMARK_URL}</span>
                    </div>

                    <div className="max-h-[320px] overflow-auto rounded-lg border border-slate-800 bg-slate-950">
                        <table className="min-w-full border-collapse text-xs">
                            <thead className="sticky top-0 z-10 bg-slate-900/95">
                                <tr>
                                    {columns.map((column) => (
                                        <th
                                            key={column}
                                            className="border-b border-slate-800 px-3 py-2 text-left font-medium text-slate-200"
                                        >
                                            {column}
                                        </th>
                                    ))}
                                </tr>
                            </thead>

                            <tbody>
                                {rows.map((row, index) => (
                                    <tr
                                        key={index}
                                        className={index % 2 === 0 ? "bg-slate-950" : "bg-slate-900/40"}
                                    >
                                        {columns.map((column) => (
                                            <td
                                                key={column}
                                                title={formatCell(row[column])}
                                                className="max-w-[220px] border-b border-slate-900 px-3 py-2 text-slate-200"
                                            >
                                                <div className="truncate">{formatCell(row[column])}</div>
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </section>
    );
}