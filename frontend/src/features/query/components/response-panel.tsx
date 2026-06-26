import { useMemo, useState } from "react";
import type {
    ExecuteResponse,
    PlanNode,
    PlanResponse,
    QueryDebug,
} from "../../../types/query";

type ResponsePanelProps = {
    title: string;
    subtitle?: string;
    data: unknown;
};

type ViewMode = "response" | "logical" | "physical" | "debug";

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function hasDebug(value: unknown): value is { debug?: QueryDebug } {
    return isObject(value) && "debug" in value;
}

function hasLogicalPlan(
    value: unknown,
): value is { logical_plan?: PlanNode | null } {
    return isObject(value) && "logical_plan" in value;
}

function hasPhysicalPlan(
    value: unknown,
): value is { physical_plan?: PlanNode | null } {
    return isObject(value) && "physical_plan" in value;
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

function formatJson(value: unknown): string {
    return JSON.stringify(value, null, 2);
}

export function ResponsePanel({
    title,
    subtitle,
    data,
}: ResponsePanelProps) {
    const [viewMode, setViewMode] = useState<ViewMode>("response");

    const tabs = useMemo(() => {
        const items: ViewMode[] = ["response"];

        if (hasLogicalPlan(data) && data.logical_plan) {
            items.push("logical");
        }

        if (hasPhysicalPlan(data) && data.physical_plan) {
            items.push("physical");
        }

        if (hasDebug(data) && data.debug) {
            items.push("debug");
        }

        return items;
    }, [data]);

    const displayText = useMemo(() => {
        switch (viewMode) {
            case "logical":
                return hasLogicalPlan(data)
                    ? formatPlan(data.logical_plan)
                    : "No logical plan available.";
            case "physical":
                return hasPhysicalPlan(data)
                    ? formatPlan(data.physical_plan)
                    : "No physical plan available.";
            case "debug":
                return hasDebug(data) && data.debug
                    ? formatJson(data.debug)
                    : "No debug output available.";
            case "response":
            default:
                return formatJson(data);
        }
    }, [data, viewMode]);

    const activeView = tabs.includes(viewMode) ? viewMode : "response";

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-white">{title}</h2>
                {subtitle ? (
                    <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
                ) : null}
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
                {tabs.map((tab) => (
                    <button
                        key={tab}
                        type="button"
                        onClick={() => setViewMode(tab)}
                        className={`rounded-md px-3 py-2 text-sm capitalize ${activeView === tab
                                ? "bg-cyan-500 text-slate-950"
                                : "border border-slate-800 bg-slate-950 text-slate-300"
                            }`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs text-slate-200">
                {displayText}
            </pre>
        </section>
    );
}