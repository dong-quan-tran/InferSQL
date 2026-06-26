type ResultTableProps = {
    columns: string[];
    rows: Record<string, unknown>[];
};

export function ResultTable({ columns, rows }: ResultTableProps) {
    if (!columns.length) {
        return (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                No columns returned.
            </div>
        );
    }

    if (!rows.length) {
        return (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                No rows returned.
            </div>
        );
    }

    return (
        <div className="max-h-[520px] overflow-auto rounded-lg border border-slate-800 bg-slate-950">
            <table className="min-w-full border-collapse text-xs">
                <thead className="bg-slate-900/80">
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
                                    className="border-b border-slate-900 px-3 py-2 text-slate-200"
                                >
                                    {formatCell(row[column])}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function formatCell(value: unknown): string {
    if (value === null || value === undefined) return "";
    if (typeof value === "number") return value.toString();
    if (typeof value === "string") return value;
    return JSON.stringify(value);
}