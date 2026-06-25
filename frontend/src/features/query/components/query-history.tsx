type QueryHistoryProps = {
    items: string[];
    onSelect: (sql: string) => void;
};

export function QueryHistory({ items, onSelect }: QueryHistoryProps) {
    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Query history</h2>
                <p className="mt-1 text-sm text-slate-400">
                    In-memory history for the current session.
                </p>
            </div>

            <div className="space-y-2">
                {items.length === 0 ? (
                    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                        No queries run yet.
                    </div>
                ) : (
                    items.map((item, index) => (
                        <button
                            key={`${index}-${item}`}
                            onClick={() => onSelect(item)}
                            className="block w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-left text-xs text-slate-300 transition hover:border-cyan-500 hover:text-white"
                        >
                            <span className="line-clamp-3 whitespace-pre-wrap">{item}</span>
                        </button>
                    ))
                )}
            </div>
        </section>
    );
}
