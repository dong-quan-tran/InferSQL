import { useMemo, useState } from "react";
import type { SavedSnippet } from "../../../types/history";
import type { PlanNode } from "../../../types/query";

type CompareView = "validate" | "plan" | "execute" | "error";

type SnippetComparePanelProps = {
    snippet: SavedSnippet | null;
};

function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
}

function renderPlanNode(node: PlanNode, depth = 0): string[] {
    const indent = "  ".repeat(depth);
    const details =
        node.details && Object.keys(node.details).length > 0
            ? ` ${JSON.stringify(node.details)}`
            : "";

    const lines = [`${indent}- ${node.node_type}${details}`];

    for (const child of node.children ?? []) {
        lines.push(...renderPlanNode(child, depth + 1));
    }

    return lines;
}

function formatPlan(plan: PlanNode | null | undefined): string {
    if (!plan) {
        return "No plan available.";
    }

    return renderPlanNode(plan).join("\n");
}

function formatTimestamp(value?: string) {
    if (!value) {
        return "Never";
    }

    const date = new Date(value);

    return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
}

function EmptyState({
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

function SummaryCard({
    label,
    value,
}: {
    label: string;
    value: string;
}) {
    return (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
            <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-2 break-words text-sm text-slate-200">{value}</p>
        </div>
    );
}

export function SnippetComparePanel({
    snippet,
}: SnippetComparePanelProps) {
    const [view, setView] = useState<CompareView>("validate");

    const tabs = useMemo(() => {
        if (!snippet?.snapshot) {
            return [] as CompareView[];
        }

        const next: CompareView[] = [];

        if (snippet.snapshot.validate) {
            next.push("validate");
        }

        if (snippet.snapshot.plan) {
            next.push("plan");
        }

        if (snippet.snapshot.execute) {
            next.push("execute");
        }

        if (snippet.snapshot.error) {
            next.push("error");
        }

        return next;
    }, [snippet]);

    const activeView = tabs.includes(view) ? view : tabs[0] ?? "validate";

    const displayText = useMemo(() => {
        if (!snippet?.snapshot) {
            return "No snapshot data available.";
        }

        switch (activeView) {
            case "validate":
                return snippet.snapshot.validate
                    ? formatJson(snippet.snapshot.validate)
                    : "No validate snapshot available.";
            case "plan":
                return snippet.snapshot.plan
                    ? [
                        "Logical plan:",
                        formatPlan(snippet.snapshot.plan.logical_plan),
                        "",
                        "Physical plan:",
                        formatPlan(snippet.snapshot.plan.physical_plan),
                        "",
                        "Full response:",
                        formatJson(snippet.snapshot.plan),
                    ].join("\n")
                    : "No plan snapshot available.";
            case "execute":
                return snippet.snapshot.execute
                    ? formatJson(snippet.snapshot.execute)
                    : "No execute snapshot available.";
            case "error":
                return snippet.snapshot.error
                    ? formatJson(snippet.snapshot.error)
                    : "No error snapshot available.";
            default:
                return "No snapshot data available.";
        }
    }, [activeView, snippet]);

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">Snippet compare</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Inspect the latest validate, plan, execute, and error snapshots for a saved snippet.
                </p>
            </div>

            {!snippet ? (
                <EmptyState
                    title="No snippet selected"
                    description="Select a saved snippet to inspect its latest query snapshots."
                />
            ) : !snippet.snapshot || tabs.length === 0 ? (
                <EmptyState
                    title="No snapshots captured yet"
                    description="Run validate, plan, or execute for SQL that matches this saved snippet to capture comparison data."
                />
            ) : (
                <div className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-2">
                        <SummaryCard label="Snippet" value={snippet.name} />
                        <SummaryCard
                            label="Last captured"
                            value={formatTimestamp(snippet.snapshot.lastRunAt)}
                        />
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {tabs.map((tab) => (
                            <button
                                key={tab}
                                type="button"
                                onClick={() => setView(tab)}
                                className={`rounded-md px-3 py-2 text-sm capitalize ${activeView === tab
                                        ? "bg-cyan-500 text-slate-950"
                                        : "border border-slate-800 bg-slate-950 text-slate-300"
                                    }`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-200">
                        {displayText}
                    </pre>
                </div>
            )}
        </section>
    );
}