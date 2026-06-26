import type { QueryHistoryEntry } from "../../../types/history";

type QueryHistoryProps = {
    items: QueryHistoryEntry[];
    onSelect: (sql: string) => void;
    onToggleFavorite: (id: string) => void;
    onDelete: (id: string) => void;
    onClear: () => void;
};

function formatTimestamp(value: string) {
    const date = new Date(value);

    return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
}

function sourceBadgeClass(source: QueryHistoryEntry["source"]) {
    switch (source) {
        case "execute":
            return "border-emerald-900 bg-emerald-950/30 text-emerald-300";
        case "plan":
            return "border-violet-900 bg-violet-950/30 text-violet-300";
        case "validate":
            return "border-cyan-900 bg-cyan-950/30 text-cyan-300";
        case "copilot":
            return "border-amber-900 bg-amber-950/30 text-amber-300";
        default:
            return "border-slate-800 bg-slate-950 text-slate-300";
    }
}

function EmptyHistoryState({
    title,
    description,
}: {
    title: string;
    description: string;
}) {
    return (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/80 p-4">
            <p className="text-sm font-medium text-slate-200">{title}</p>
            <p className="mt-1 text-sm text-slate-400">{description}</p>
        </div>
    );
}

function HistoryCard({
    item,
    onSelect,
    onToggleFavorite,
    onDelete,
}: {
    item: QueryHistoryEntry;
    onSelect: (sql: string) => void;
    onToggleFavorite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4">
            <div className="mb-3 flex flex-wrap items-center gap-2">
                <span
                    className={`rounded-md border px-2 py-1 text-[11px] ${sourceBadgeClass(
                        item.source,
                    )}`}
                >
                    {item.source}
                </span>
                <span className="text-xs text-slate-500">{formatTimestamp(item.createdAt)}</span>
                {item.favorite ? (
                    <span className="rounded-md border border-amber-800 bg-amber-950/40 px-2 py-1 text-[11px] text-amber-200">
                        Favorite
                    </span>
                ) : null}
            </div>

            <pre className="max-h-28 overflow-auto whitespace-pre-wrap break-words rounded-md bg-slate-900/70 p-3 text-xs text-slate-200">
                {item.sql}
            </pre>

            <div className="mt-3 flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => onSelect(item.sql)}
                    className="rounded-md bg-cyan-500 px-3 py-2 text-xs font-medium text-slate-950 transition hover:bg-cyan-400"
                >
                    Load into editor
                </button>

                <button
                    type="button"
                    onClick={() => onToggleFavorite(item.id)}
                    className={`rounded-md px-3 py-2 text-xs transition ${item.favorite
                            ? "border border-amber-800 bg-amber-950/30 text-amber-200 hover:bg-amber-950/50"
                            : "border border-slate-700 bg-slate-900 text-slate-200 hover:border-amber-800 hover:text-amber-200"
                        }`}
                >
                    {item.favorite ? "Unfavorite" : "Favorite"}
                </button>

                <button
                    type="button"
                    onClick={() => onDelete(item.id)}
                    className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-300 transition hover:border-rose-800 hover:text-rose-200"
                >
                    Delete
                </button>
            </div>
        </div>
    );
}

export function QueryHistory({
    items,
    onSelect,
    onToggleFavorite,
    onDelete,
    onClear,
}: QueryHistoryProps) {
    const favorites = items.filter((item) => item.favorite);
    const recents = items.filter((item) => !item.favorite);

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-white">Query history</h2>
                    <p className="mt-1 text-sm text-slate-400">
                        Session queries, favorites, and quick editor reloads.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={onClear}
                    disabled={items.length === 0}
                    className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300 transition hover:border-rose-800 hover:text-rose-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Clear all
                </button>
            </div>

            {items.length === 0 ? (
                <EmptyHistoryState
                    title="No saved queries yet"
                    description="Run validate, plan, execute, or save the current editor text to start building session history."
                />
            ) : (
                <div className="space-y-5">
                    <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                            Favorites
                        </p>

                        {favorites.length === 0 ? (
                            <EmptyHistoryState
                                title="No favorites yet"
                                description="Star your most useful queries so they stay easy to find during demos and iteration."
                            />
                        ) : (
                            <div className="space-y-3">
                                {favorites.map((item) => (
                                    <HistoryCard
                                        key={item.id}
                                        item={item}
                                        onSelect={onSelect}
                                        onToggleFavorite={onToggleFavorite}
                                        onDelete={onDelete}
                                    />
                                ))}
                            </div>
                        )}
                    </div>

                    <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                            Recent
                        </p>

                        {recents.length === 0 ? (
                            <EmptyHistoryState
                                title="No recent queries yet"
                                description="Recent validate, plan, execute, and copilot actions will appear here."
                            />
                        ) : (
                            <div className="space-y-3">
                                {recents.map((item) => (
                                    <HistoryCard
                                        key={item.id}
                                        item={item}
                                        onSelect={onSelect}
                                        onToggleFavorite={onToggleFavorite}
                                        onDelete={onDelete}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </section>
    );
}