import type { CatalogDataset } from "../../../types/catalog";

type DatasetDetailProps = {
    dataset: CatalogDataset | null;
    onInsertSql: (sql: string) => void;
};

export function DatasetDetail({ dataset, onInsertSql }: DatasetDetailProps) {
    if (!dataset) {
        return (
            <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                <div className="text-sm text-slate-400">
                    Select a dataset to inspect its schema and metadata.
                </div>
            </section>
        );
    }

    const columns = dataset.columns ?? [];

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">{dataset.name}</h2>
                    <p className="mt-1 text-sm text-slate-400">
                        {dataset.description || "No description"}
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() =>
                            onInsertSql(`SELECT *\nFROM ${dataset.name}\nLIMIT 10`)
                        }
                        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white"
                    >
                        Insert SELECT *
                    </button>

                    <button
                        onClick={() => {
                            const firstColumn = columns[0]?.name ?? "*";
                            onInsertSql(
                                `SELECT ${firstColumn}\nFROM ${dataset.name}\nLIMIT 10`,
                            );
                        }}
                        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition hover:border-cyan-500 hover:text-white"
                    >
                        Insert starter query
                    </button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Rows</p>
                    <p className="mt-2 text-sm text-slate-200">
                        {dataset.row_count ?? "unknown"}
                    </p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                        Columns
                    </p>
                    <p className="mt-2 text-sm text-slate-200">{columns.length}</p>
                </div>

                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">
                        Source
                    </p>
                    <p className="mt-2 break-words text-sm text-slate-200">
                        {dataset.source_path || "unknown"}
                    </p>
                </div>
            </div>

            <div className="mt-5">
                <h3 className="mb-3 text-sm font-semibold text-white">Schema</h3>

                {!columns.length ? (
                    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                        No schema columns available.
                    </div>
                ) : (
                    <div className="overflow-auto rounded-lg border border-slate-800 bg-slate-950">
                        <table className="min-w-full border-collapse text-sm">
                            <thead className="bg-slate-900/80">
                                <tr>
                                    <th className="border-b border-slate-800 px-3 py-2 text-left text-slate-200">
                                        Name
                                    </th>
                                    <th className="border-b border-slate-800 px-3 py-2 text-left text-slate-200">
                                        Type
                                    </th>
                                    <th className="border-b border-slate-800 px-3 py-2 text-left text-slate-200">
                                        Description
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {columns.map((column, index) => (
                                    <tr
                                        key={`${column.name}-${index}`}
                                        className={
                                            index % 2 === 0 ? "bg-slate-950" : "bg-slate-900/40"
                                        }
                                    >
                                        <td className="border-b border-slate-900 px-3 py-2 text-slate-200">
                                            {column.name}
                                        </td>
                                        <td className="border-b border-slate-900 px-3 py-2 text-slate-300">
                                            {column.type || "unknown"}
                                        </td>
                                        <td className="border-b border-slate-900 px-3 py-2 text-slate-400">
                                            {column.description || ""}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </section>
    );
}