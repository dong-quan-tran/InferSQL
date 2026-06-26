export type QueryHistorySource = "validate" | "plan" | "execute" | "copilot";

export type QueryHistoryEntry = {
    id: string;
    sql: string;
    source: QueryHistorySource;
    createdAt: string;
    favorite: boolean;
};