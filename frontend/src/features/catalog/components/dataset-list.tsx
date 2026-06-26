import type { CatalogDataset } from "../../../types/catalog";

type DatasetListProps = {
    datasets: CatalogDataset[];
    selectedName: string | null;
    onSelect: (name: string) => void;
};

export function DatasetList({
    datasets,
    selectedName,
    onSelect,
}: DatasetListProps) {
    if (!datasets.length) {
        return (
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400">
                No datasets available.
            </div>
        );
    }

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Datasets</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Browse registered datasets.
                </p>
            </div>

            <div className="space-y-2">
                {datasets.map((dataset) => {
                    const isSelected = dataset.name === selectedName;

                    return (
                        <button
                            key={dataset.name}
                            onClick={() => onSelect(dataset.name)}
                            className={`block w-full rounded-lg border p-3 text-left transition ${isSelected
                                ? "border-cyan-500 bg-slate-950 text-white"
                                : "border-slate-800 bg-slate-950 text-slate-300 hover:border-cyan-500"
                                }`}
                        >
                            <p className="font-medium">{dataset.name}</p>
                            <p className="mt-1 text-xs text-slate-400">
                                {dataset.description || "No description"}
                            </p>
                            <p className="mt-2 text-xs text-slate-500">
                                Rows: {dataset.row_count ?? "unknown"}
                            </p>
                        </button>
                    );
                })}
            </div>
        </section>
    );
}