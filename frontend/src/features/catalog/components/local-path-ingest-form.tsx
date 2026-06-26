import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../../lib/api/client";
import {
    ingestFromPath,
    type DatasetIngestResponse,
} from "../ingest-api";

function getErrorMessage(error: unknown): string {
    if (error instanceof ApiError) {
        const payload = error.payload as
            | { error?: { message?: string } }
            | undefined;

        return payload?.error?.message || error.message;
    }

    if (error instanceof Error) {
        return error.message;
    }

    return "Unknown error";
}

export function LocalPathIngestForm() {
    const queryClient = useQueryClient();

    const [name, setName] = useState("");
    const [path, setPath] = useState("");
    const [description, setDescription] = useState("");
    const [overwrite, setOverwrite] = useState(false);

    const mutation = useMutation<DatasetIngestResponse, Error>({
        mutationFn: () =>
            ingestFromPath({
                name: name.trim(),
                path: path.trim(),
                description: description.trim(),
                overwrite,
            }),
        onSuccess: async () => {
            setName("");
            setPath("");
            setDescription("");
            setOverwrite(false);

            await queryClient.invalidateQueries({ queryKey: ["catalog-datasets"] });
        },
    });

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        mutation.mutate();
    }

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Ingest from path</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Register a local CSV or Parquet file by server-side path.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <label className="block">
                    <span className="mb-1 block text-sm text-slate-300">Dataset name</span>
                    <input
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="prices_new"
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block text-sm text-slate-300">File path</span>
                    <input
                        value={path}
                        onChange={(event) => setPath(event.target.value)}
                        placeholder="data/prices.csv"
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500"
                    />
                </label>

                <label className="block">
                    <span className="mb-1 block text-sm text-slate-300">Description</span>
                    <textarea
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        placeholder="Optional dataset description"
                        rows={3}
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-500"
                    />
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-300">
                    <input
                        type="checkbox"
                        checked={overwrite}
                        onChange={(event) => setOverwrite(event.target.checked)}
                        className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500"
                    />
                    Overwrite if dataset name already exists
                </label>

                <button
                    type="submit"
                    disabled={mutation.isPending || !name.trim() || !path.trim()}
                    className="rounded-md bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {mutation.isPending ? "Ingesting..." : "Ingest dataset"}
                </button>

                {mutation.isSuccess ? (
                    <div className="rounded-lg border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-200">
                        Ingested <span className="font-medium">{mutation.data.name}</span> (
                        {mutation.data.row_count} rows).
                    </div>
                ) : null}

                {mutation.isError ? (
                    <div className="rounded-lg border border-rose-900 bg-rose-950/40 p-3 text-sm text-rose-200">
                        {getErrorMessage(mutation.error)}
                    </div>
                ) : null}
            </form>
        </section>
    );
}