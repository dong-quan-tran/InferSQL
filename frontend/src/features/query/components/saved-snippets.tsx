import type { SavedSnippet } from "../../../types/history";

type SavedSnippetsProps = {
    items: SavedSnippet[];
    selectedId: string | null;
    onSelect: (sql: string) => void;
    onSelectSnippet: (id: string) => void;
    onRename: (id: string, name: string) => void;
    onToggleFavorite: (id: string) => void;
    onDelete: (id: string) => void;
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

function EmptySnippetState({
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

function SnippetCard({
    item,
    selectedId,
    onSelect,
    onSelectSnippet,
    onRename,
    onToggleFavorite,
    onDelete,
}: {
    item: SavedSnippet;
    selectedId: string | null;
    onSelect: (sql: string) => void;
    onSelectSnippet: (id: string) => void;
    onRename: (id: string, name: string) => void;
    onToggleFavorite: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    function handleRename() {
        const nextName = window.prompt("Rename snippet", item.name);

        if (!nextName) {
            return;
        }

        const trimmed = nextName.trim();
        if (!trimmed || trimmed === item.name) {
            return;
        }

        onRename(item.id, trimmed);
    }

    const isSelected = selectedId === item.id;

    return (
        <div
            className={`rounded-lg border p-4 ${isSelected
                    ? "border-cyan-700 bg-slate-950"
                    : "border-slate-800 bg-slate-950"
                }`}
        >
            <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-cyan-900 bg-cyan-950/30 px-2 py-1 text-[11px] text-cyan-300">
                    Snippet
                </span>
                <span className="text-sm font-medium text-slate-200">{item.name}</span>
                <span className="text-xs text-slate-500">
                    Updated {formatTimestamp(item.updatedAt)}
                </span>
                {item.favorite ? (
                    <span className="rounded-md border border-amber-800 bg-amber-950/40 px-2 py-1 text-[11px] text-amber-200">
                        Pinned
                    </span>
                ) : null}
                {item.snapshot?.lastRunAt ? (
                    <span className="rounded-md border border-emerald-800 bg-emerald-950/30 px-2 py-1 text-[11px] text-emerald-300">
                        Snapshot
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
                    onClick={() => onSelectSnippet(item.id)}
                    className={`rounded-md px-3 py-2 text-xs transition ${isSelected
                            ? "border border-cyan-700 bg-cyan-950/30 text-cyan-200"
                            : "border border-slate-700 bg-slate-900 text-slate-200 hover:border-cyan-700 hover:text-cyan-200"
                        }`}
                >
                    {isSelected ? "Comparing" : "Compare"}
                </button>

                <button
                    type="button"
                    onClick={handleRename}
                    className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 transition hover:border-cyan-700 hover:text-cyan-200"
                >
                    Rename
                </button>

                <button
                    type="button"
                    onClick={() => onToggleFavorite(item.id)}
                    className={`rounded-md px-3 py-2 text-xs transition ${item.favorite
                            ? "border border-amber-800 bg-amber-950/30 text-amber-200 hover:bg-amber-950/50"
                            : "border border-slate-700 bg-slate-900 text-slate-200 hover:border-amber-800 hover:text-amber-200"
                        }`}
                >
                    {item.favorite ? "Unpin" : "Pin"}
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

export function SavedSnippets({
    items,
    selectedId,
    onSelect,
    onSelectSnippet,
    onRename,
    onToggleFavorite,
    onDelete,
}: SavedSnippetsProps) {
    const pinned = items.filter((item) => item.favorite);
    const unpinned = items.filter((item) => !item.favorite);

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Saved snippets</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Durable named SQL snippets stored locally across browser reloads.
                </p>
            </div>

            {items.length === 0 ? (
                <EmptySnippetState
                    title="No snippets yet"
                    description="Save reusable SQL from the editor to build a durable snippet library."
                />
            ) : (
                <div className="space-y-5">
                    <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                            Pinned
                        </p>

                        {pinned.length === 0 ? (
                            <EmptySnippetState
                                title="No pinned snippets yet"
                                description="Pin your most useful reusable SQL so it stays easy to find."
                            />
                        ) : (
                            <div className="space-y-3">
                                {pinned.map((item) => (
                                    <SnippetCard
                                        key={item.id}
                                        item={item}
                                        selectedId={selectedId}
                                        onSelect={onSelect}
                                        onSelectSnippet={onSelectSnippet}
                                        onRename={onRename}
                                        onToggleFavorite={onToggleFavorite}
                                        onDelete={onDelete}
                                    />
                                ))}
                            </div>
                        )}
                    </div>

                    <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                            All snippets
                        </p>

                        {unpinned.length === 0 ? (
                            <EmptySnippetState
                                title="No additional snippets yet"
                                description="Saved snippets that are not pinned will appear here."
                            />
                        ) : (
                            <div className="space-y-3">
                                {unpinned.map((item) => (
                                    <SnippetCard
                                        key={item.id}
                                        item={item}
                                        selectedId={selectedId}
                                        onSelect={onSelect}
                                        onSelectSnippet={onSelectSnippet}
                                        onRename={onRename}
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