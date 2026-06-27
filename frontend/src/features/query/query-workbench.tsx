import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ApiError } from "../../lib/api/client";
import type {
    QueryHistoryEntry,
    QueryHistorySource,
    SavedSnippet,
    SavedSnippetSnapshot,
} from "../../types/history";
import type {
    ErrorResponse,
    ExecuteResponse,
    PlanResponse,
    ValidateResponse,
} from "../../types/query";
import { executeSql, planSql, validateSql } from "./api";
import { BenchmarkViewer } from "./components/benchmark-viewer";
import { QueryHistory } from "./components/query-history";
import { ResponsePanel } from "./components/response-panel";
import { ResultChart } from "./components/result-chart";
import { ResultTable } from "./components/result-table";
import { SavedSnippets } from "./components/saved-snippets";
import { SnippetComparePanel } from "./components/snippet-compare-panel";
import { SqlEditor } from "./components/sql-editor";

type ActiveTab = "validate" | "plan" | "execute" | "error";

type QueryWorkbenchProps = {
    sql: string;
    onSqlChange: (value: string) => void;
    history: QueryHistoryEntry[];
    snippets: SavedSnippet[];
    onSaveHistory: (sql: string, source: QueryHistorySource) => void;
    onSaveSnippet: (sql: string) => void;
    onSaveSnippetSnapshot: (sql: string, snapshot: SavedSnippetSnapshot) => void;
    onRenameSnippet: (id: string, name: string) => void;
    onToggleSnippetFavorite: (id: string) => void;
    onDeleteSnippet: (id: string) => void;
    onToggleFavorite: (id: string) => void;
    onDeleteHistory: (id: string) => void;
    onClearHistory: () => void;
};

function extractErrorPayload(
    error: unknown,
): ErrorResponse | { message: string } {
    if (error instanceof ApiError) {
        if (typeof error.payload === "object" && error.payload !== null) {
            return error.payload as ErrorResponse;
        }

        return { message: error.message };
    }

    if (error instanceof Error) {
        return { message: error.message };
    }

    return { message: "Unknown error" };
}

export function QueryWorkbench({
    sql,
    onSqlChange,
    history,
    snippets,
    onSaveHistory,
    onSaveSnippet,
    onSaveSnippetSnapshot,
    onRenameSnippet,
    onToggleSnippetFavorite,
    onDeleteSnippet,
    onToggleFavorite,
    onDeleteHistory,
    onClearHistory,
}: QueryWorkbenchProps) {
    const [activeTab, setActiveTab] = useState<ActiveTab>("execute");
    const [selectedSnippetId, setSelectedSnippetId] = useState<string | null>(null);

    const validateMutation = useMutation<ValidateResponse, Error, { sql: string }>({
        mutationFn: validateSql,
        onSuccess: (data, variables) => {
            setActiveTab("validate");
            onSaveSnippetSnapshot(variables.sql, { validate: data });
        },
        onError: (error, variables) => {
            setActiveTab("error");
            onSaveSnippetSnapshot(variables.sql, { error: extractErrorPayload(error) });
        },
    });

    const planMutation = useMutation<PlanResponse, Error, { sql: string }>({
        mutationFn: planSql,
        onSuccess: (data, variables) => {
            setActiveTab("plan");
            onSaveSnippetSnapshot(variables.sql, { plan: data });
        },
        onError: (error, variables) => {
            setActiveTab("error");
            onSaveSnippetSnapshot(variables.sql, { error: extractErrorPayload(error) });
        },
    });

    const executeMutation = useMutation<ExecuteResponse, Error, { sql: string }>({
        mutationFn: executeSql,
        onSuccess: (data, variables) => {
            setActiveTab("execute");
            onSaveSnippetSnapshot(variables.sql, { execute: data });
        },
        onError: (error, variables) => {
            setActiveTab("error");
            onSaveSnippetSnapshot(variables.sql, { error: extractErrorPayload(error) });
        },
    });

    const latestError =
        validateMutation.error || planMutation.error || executeMutation.error;

    const panelData = useMemo(() => {
        switch (activeTab) {
            case "validate":
                return validateMutation.data ?? { message: "No validate response yet." };
            case "plan":
                return planMutation.data ?? { message: "No plan response yet." };
            case "execute":
                return executeMutation.data ?? { message: "No execute response yet." };
            case "error":
                return extractErrorPayload(latestError);
            default:
                return { message: "No data available." };
        }
    }, [
        activeTab,
        executeMutation.data,
        latestError,
        planMutation.data,
        validateMutation.data,
    ]);

    const selectedSnippet = useMemo(
        () => snippets.find((item) => item.id === selectedSnippetId) ?? null,
        [selectedSnippetId, snippets],
    );

    function handleRun(source: QueryHistorySource, runner: () => void) {
        onSaveHistory(sql, source);
        runner();
    }

    function handleSaveCurrent() {
        onSaveSnippet(sql);
    }

    return (
        <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-6">
                <SqlEditor
                    value={sql}
                    onChange={onSqlChange}
                    onValidate={() => handleRun("validate", () => validateMutation.mutate({ sql }))}
                    onPlan={() => handleRun("plan", () => planMutation.mutate({ sql }))}
                    onExecute={() => handleRun("execute", () => executeMutation.mutate({ sql }))}
                    isValidating={validateMutation.isPending}
                    isPlanning={planMutation.isPending}
                    isExecuting={executeMutation.isPending}
                />

                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setActiveTab("validate")}
                        className={`rounded-md px-3 py-2 text-sm ${activeTab === "validate"
                            ? "bg-cyan-500 text-slate-950"
                            : "border border-slate-800 bg-slate-950 text-slate-300"
                            }`}
                    >
                        Validate
                    </button>

                    <button
                        onClick={() => setActiveTab("plan")}
                        className={`rounded-md px-3 py-2 text-sm ${activeTab === "plan"
                            ? "bg-cyan-500 text-slate-950"
                            : "border border-slate-800 bg-slate-950 text-slate-300"
                            }`}
                    >
                        Plan
                    </button>

                    <button
                        onClick={() => setActiveTab("execute")}
                        className={`rounded-md px-3 py-2 text-sm ${activeTab === "execute"
                            ? "bg-cyan-500 text-slate-950"
                            : "border border-slate-800 bg-slate-950 text-slate-300"
                            }`}
                    >
                        Execute
                    </button>

                    <button
                        onClick={() => setActiveTab("error")}
                        className={`rounded-md px-3 py-2 text-sm ${activeTab === "error"
                            ? "bg-rose-500 text-white"
                            : "border border-slate-800 bg-slate-950 text-slate-300"
                            }`}
                    >
                        Error
                    </button>

                    <button
                        onClick={handleSaveCurrent}
                        disabled={!sql.trim()}
                        className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 transition hover:border-cyan-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Save snippet
                    </button>
                </div>

                <ResponsePanel
                    title="Response"
                    subtitle="Structured response, plans, and debug output for the selected action."
                    data={panelData}
                />
            </div>

            <div className="space-y-6">
                <SavedSnippets
                    items={snippets}
                    selectedId={selectedSnippetId}
                    onSelect={onSqlChange}
                    onSelectSnippet={setSelectedSnippetId}
                    onRename={onRenameSnippet}
                    onToggleFavorite={onToggleSnippetFavorite}
                    onDelete={onDeleteSnippet}
                />

                <SnippetComparePanel snippet={selectedSnippet} />

                <QueryHistory
                    items={history}
                    onSelect={onSqlChange}
                    onToggleFavorite={onToggleFavorite}
                    onDelete={onDeleteHistory}
                    onClear={onClearHistory}
                />

                <BenchmarkViewer />

                <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
                    <div className="mb-4">
                        <h2 className="text-lg font-semibold text-white">Aggregate chart</h2>
                        <p className="mt-1 text-sm text-slate-400">
                            Lightweight chart for simple aggregate-style execute results.
                        </p>
                    </div>

                    <ResultChart
                        columns={executeMutation.data?.columns ?? []}
                        rows={executeMutation.data?.rows ?? []}
                    />
                </section>

                <ResultTable
                    title="Latest execute rows"
                    columns={executeMutation.data?.columns ?? []}
                    rows={executeMutation.data?.rows ?? []}
                />
            </div>
        </div>
    );
}