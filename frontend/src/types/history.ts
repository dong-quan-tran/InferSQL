import type {
    ErrorResponse,
    ExecuteResponse,
    PlanResponse,
    ValidateResponse,
} from "./query";

export type QueryHistorySource = "validate" | "plan" | "execute" | "copilot";

export type QueryHistoryEntry = {
    id: string;
    sql: string;
    source: QueryHistorySource;
    createdAt: string;
    favorite: boolean;
};

export type SavedSnippetSnapshot = {
    validate?: ValidateResponse;
    plan?: PlanResponse;
    execute?: ExecuteResponse;
    error?: ErrorResponse | { message: string };
    lastRunAt?: string;
};

export type SavedSnippet = {
    id: string;
    name: string;
    sql: string;
    createdAt: string;
    updatedAt: string;
    favorite: boolean;
    snapshot?: SavedSnippetSnapshot;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

export function isQueryHistorySource(value: unknown): value is QueryHistorySource {
    return (
        value === "validate" ||
        value === "plan" ||
        value === "execute" ||
        value === "copilot"
    );
}

export function isQueryHistoryEntry(value: unknown): value is QueryHistoryEntry {
    return (
        isRecord(value) &&
        typeof value.id === "string" &&
        typeof value.sql === "string" &&
        isQueryHistorySource(value.source) &&
        typeof value.createdAt === "string" &&
        typeof value.favorite === "boolean"
    );
}

function isSavedSnippetSnapshot(value: unknown): value is SavedSnippetSnapshot {
    if (!isRecord(value)) {
        return false;
    }

    if ("lastRunAt" in value && typeof value.lastRunAt !== "string") {
        return false;
    }

    return true;
}

export function isSavedSnippet(value: unknown): value is SavedSnippet {
    return (
        isRecord(value) &&
        typeof value.id === "string" &&
        typeof value.name === "string" &&
        typeof value.sql === "string" &&
        typeof value.createdAt === "string" &&
        typeof value.updatedAt === "string" &&
        typeof value.favorite === "boolean" &&
        (!("snapshot" in value) ||
            value.snapshot === undefined ||
            isSavedSnippetSnapshot(value.snapshot))
    );
}