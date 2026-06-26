type ResultTableProps = {
    columns: string[];
    rows: Record<string, unknown>[];
    title?: string;
};

function formatCell(value: unknown): string {
    if (value === null || value === undefined) return "null";
    if (typeof value === "number") return value.toString();
    if (typeof value === "string") return value;
    if (typeof value === "boolean") return value ? "true" : "false";
    return JSON.stringify(value);
}

function escapeCsvCell(value: unknown): string {
    const text =
        value === null || value === undefined ? "" : String(formatCell(value));
    const escaped = text.replace(/"/g, `""`);
    return `"${escaped}"`;
}

function downloadCsv(columns: string[], rows: Record<string, unknown>[]) {
    const csvLines = [
        columns.map((column) => escapeCsvCell(column)).join(","),
        ...rows.map((row) =>
            columns.map((column) => escapeCsvCell(row[column])).join(","),
        ),
    ];

    const blob = new Blob([csvLines.join("\n")], {
        type: "text/csv;charset=utf-8;",
    });

    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

    link.href = url;
    link.download = `infersql-result-${timestamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

export function ResultTable({
    columns,
    rows,
    title = "Result table",
}: ResultTableProps) {
    if (!columns.length) {
        return (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                No columns returned.
            </div>
        );
    }

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-white">{title}</h2>
                    <p className="mt-1 text-sm text-slate-400">
                        {rows.length} row{rows.length === 1 ? "" : "s"} · {columns.length} column
                        {columns.length === 1 ? "" : "s"}
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => downloadCsv(columns, rows)}
                    disabled={!rows.length}
                    className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300 transition hover:border-cyan-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Export CSV
                </button>
            </div>

            {!rows.length ? (
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                    No rows returned.
                </div>
            ) : (
                <div className="max-h-[520px] overflow-auto rounded-lg border border-slate-800 bg-slate-950">
                    <table className="min-w-full border-collapse text-xs">
                        <thead className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur">
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
                                    className={
                                        index % 2 === 0 ? "bg-slate-950" : "bg-slate-900/40"
                                    }
                                >
                                    {columns.map((column) => {
                                        const value = row[column];
                                        const display = formatCell(value);
                                        const isNull = value === null || value === undefined;

                                        return (
                                            <td
                                                key={column}
                                                title={display}
                                                className={`max-w-[240px] border-b border-slate-900 px-3 py-2 align-top ${isNull ? "text-slate-500 italic" : "text-slate-200"
                                                    }`}
                                            >
                                                <div className="truncate">{display}</div>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}