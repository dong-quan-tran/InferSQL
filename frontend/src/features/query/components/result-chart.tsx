type ResultChartProps = {
    columns: string[];
    rows: Record<string, unknown>[];
};

type ChartPoint = {
    label: string;
    value: number;
};

function getChartPoints(
    columns: string[],
    rows: Record<string, unknown>[],
): ChartPoint[] | null {
    if (columns.length < 2 || !rows.length) {
        return null;
    }

    for (let valueIndex = 1; valueIndex < columns.length; valueIndex += 1) {
        const labelColumn = columns[0];
        const valueColumn = columns[valueIndex];

        const points = rows
            .map((row) => ({
                label: String(row[labelColumn] ?? ""),
                value: row[valueColumn],
            }))
            .filter((point) => point.label.length > 0);

        if (!points.length) {
            continue;
        }

        const allNumeric = points.every(
            (point) => typeof point.value === "number" && Number.isFinite(point.value),
        );

        if (!allNumeric) {
            continue;
        }

        return points
            .map((point) => ({
                label: point.label,
                value: point.value as number,
            }))
            .slice(0, 12);
    }

    return null;
}

function formatValue(value: number) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 2,
    }).format(value);
}

export function ResultChart({ columns, rows }: ResultChartProps) {
    const points = getChartPoints(columns, rows);

    if (!points?.length) {
        return (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                No lightweight chart available for this result shape.
            </div>
        );
    }

    const maxValue = Math.max(...points.map((point) => point.value), 1);

    return (
        <div className="space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4">
            {points.map((point) => {
                const width = `${Math.max((point.value / maxValue) * 100, 4)}%`;

                return (
                    <div key={point.label} className="space-y-1">
                        <div className="flex items-center justify-between gap-3 text-xs">
                            <span className="truncate text-slate-300">{point.label}</span>
                            <span className="text-slate-400">{formatValue(point.value)}</span>
                        </div>

                        <div className="h-2 rounded-full bg-slate-900">
                            <div
                                className="h-2 rounded-full bg-cyan-500"
                                style={{ width }}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}