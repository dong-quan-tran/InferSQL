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
        <div className="grid gap-6 p-6 xl:grid-cols-[320px_minmax(0,1fr)]">
            <div className="space-y-6">
                {datasetsQuery.isLoading ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400">
                        Loading datasets...
                    </div>
                ) : datasetsQuery.isError ? (
                    <div className="rounded-xl border border-rose-900 bg-rose-950/40 p-5 text-sm text-rose-200">
                        Failed to load datasets.
                    </div>
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

            <div>
                {detailQuery.isLoading ? (
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400">
                        Loading dataset detail...
                    </div>
                ) : detailQuery.isError ? (
                    <div className="rounded-xl border border-rose-900 bg-rose-950/40 p-5 text-sm text-rose-200">
                        Failed to load dataset detail.
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