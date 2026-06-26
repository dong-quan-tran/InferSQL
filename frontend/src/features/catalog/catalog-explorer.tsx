import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDatasetDetail, fetchDatasets } from "./api";
import { DatasetDetail } from "./components/dataset-detail";
import { DatasetList } from "./components/dataset-list";
import { LocalPathIngestForm } from "./components/local-path-ingest-form";
import { UploadIngestForm } from "./components/upload-ingest-form";

type CatalogExplorerProps = {
    onInsertSql: (sql: string) => void;
};

function EmptyState({
    title,
    description,
}: {
    title: string;
    description: string;
}) {
    return (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-5">
            <h2 className="text-base font-medium text-white">{title}</h2>
            <p className="mt-2 text-sm text-slate-400">{description}</p>
        </div>
    );
}

export function CatalogExplorer({ onInsertSql }: CatalogExplorerProps) {
    const [selectedName, setSelectedName] = useState<string | null>(null);

    const datasetsQuery = useQuery({
        queryKey: ["catalog-datasets"],
        queryFn: fetchDatasets,
    });

    const datasets = datasetsQuery.data?.datasets ?? [];

    useEffect(() => {
        if (!selectedName && datasets.length > 0) {
            setSelectedName(datasets[0].name);
            return;
        }

        if (
            selectedName &&
            datasets.length > 0 &&
            !datasets.some((dataset) => dataset.name === selectedName)
        ) {
            setSelectedName(datasets[0].name);
        }
    }, [datasets, selectedName]);

    const detailQuery = useQuery({
        queryKey: ["catalog-dataset-detail", selectedName],
        queryFn: () => fetchDatasetDetail(selectedName!),
        enabled: !!selectedName,
    });

    function handleDatasetIngested(datasetName: string) {
        setSelectedName(datasetName);
    }

    return (
        <div className="grid gap-6 p-4 sm:p-6 xl:grid-cols-[320px_minmax(0,1fr)]">
            <div className="space-y-6">
                {datasetsQuery.isLoading ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400">
                        Loading datasets...
                    </div>
                ) : datasetsQuery.isError ? (
                    <div className="rounded-xl border border-rose-900 bg-rose-950/40 p-5 text-sm text-rose-200">
                        Dataset catalog is unavailable right now. Check the API connection and try again.
                    </div>
                ) : datasets.length === 0 ? (
                    <EmptyState
                        title="No datasets registered"
                        description="Ingest a local path or upload a file to populate the catalog and unlock SQL suggestions."
                    />
                ) : (
                    <DatasetList
                        datasets={datasets}
                        selectedName={selectedName}
                        onSelect={setSelectedName}
                    />
                )}

                <LocalPathIngestForm onSuccess={handleDatasetIngested} />
                <UploadIngestForm onSuccess={handleDatasetIngested} />
            </div>

            <div className="min-w-0">
                {!selectedName && !datasets.length ? (
                    <EmptyState
                        title="Choose a dataset"
                        description="Dataset schema, columns, and sample-driven SQL helpers will appear here after ingest."
                    />
                ) : detailQuery.isLoading ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400">
                        Loading dataset detail...
                    </div>
                ) : detailQuery.isError ? (
                    <div className="rounded-xl border border-rose-900 bg-rose-950/40 p-5 text-sm text-rose-200">
                        Failed to load dataset detail for the selected dataset.
                    </div>
                ) : (
                    <DatasetDetail
                        dataset={detailQuery.data ?? null}
                        onInsertSql={onInsertSql}
                    />
                )}
            </div>
        </div>
    );
}