import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ApiError } from "../../lib/api/client";
import type {
    ErrorResponse,
    ExecuteResponse,
    PlanResponse,
    ValidateResponse,
} from "../../types/query";
import { executeSql, planSql, validateSql } from "./api";
import { QueryHistory } from "./components/query-history";
import { ResponsePanel } from "./components/response-panel";
import { SqlEditor } from "./components/sql-editor";

const STARTER_SQL = `SELECT symbol, close
FROM prices
WHERE close > 100
ORDER BY close DESC
LIMIT 10`;

type ActiveTab = "validate" | "plan" | "execute" | "error";

function extractErrorPayload(error: unknown): ErrorResponse | { message: string } {
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

export function QueryWorkbench() {
    const [sql, setSql] = useState(STARTER_SQL);
    const [history, setHistory] = useState<string[]>([]);
    const [activeTab, setActiveTab] = useState<ActiveTab>("execute");

    const validateMutation = useMutation<ValidateResponse, Error, { sql: string }>({
        mutationFn: validateSql,
        onSuccess: () => setActiveTab("validate"),
        onError: () => setActiveTab("error"),
    });

    const planMutation = useMutation<PlanResponse, Error, { sql: string }>({
        mutationFn: planSql,
        onSuccess: () => setActiveTab("plan"),
        onError: () => setActiveTab("error"),
    });

    const executeMutation = useMutation<ExecuteResponse, Error, { sql: string }>({
        mutationFn: executeSql,
        onSuccess: () => setActiveTab("execute"),
        onError: () => setActiveTab("error"),
    });

    const latestError = validateMutation.error || planMutation.error || executeMutation.error;

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

    function pushHistory(nextSql: string) {
        const trimmed = nextSql.trim();
        if (!trimmed) return;

        setHistory((current) => {
            const withoutDuplicate = current.filter((item) => item !== trimmed);
            return [trimmed, ...withoutDuplicate].slice(0, 10);
        });
    }

    function handleValidate() {
        pushHistory(sql);
        validateMutation.mutate({ sql });
    }

    function handlePlan() {
        pushHistory(sql);
        planMutation.mutate({ sql });
    }

    function handleExecute() {
        pushHistory(sql);
        executeMutation.mutate({ sql });
    }

    return (
        <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-6">
                <SqlEditor
                    value={sql}
                    onChange={setSql}
                    onValidate={handleValidate}
                    onPlan={handlePlan}
                    onExecute={handleExecute}
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
                </div>

                <ResponsePanel
                    title="Response"
                    subtitle="Raw JSON response from the selected action."
                    data={panelData}
                />
            </div>

            <div className="space-y-6">
                <QueryHistory items={history} onSelect={setSql} />

                <ResponsePanel
                    title="Latest execute rows"
                    subtitle="Convenience view for the most recent execute result."
                    data={executeMutation.data?.rows ?? []}
                />
            </div>
        </div>
    );
}