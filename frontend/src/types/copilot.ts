export type CopilotQueryRequest = {
    question: string;
    execute: boolean;
};

export type CopilotSqlCandidate = {
    sql: string;
    assumptions: string[];
    referenced_tables: string[];
    referenced_columns: string[];
    confidence: number;
};

export type CopilotValidationResult = {
    is_valid: boolean;
    normalized_sql: string;
    errors: string[];
    tables: string[];
    columns: string[];
    query_type?: string | null;
    has_where: boolean;
    has_group_by: boolean;
    has_order_by: boolean;
    has_limit: boolean;
};

export type CopilotRetryStep = {
    attempt: number;
    candidate: CopilotSqlCandidate;
    validation: CopilotValidationResult;
};

export type CopilotQueryResponse = {
    question: string;
    provider: string;
    model: string;
    candidate: CopilotSqlCandidate;
    validation: CopilotValidationResult;
    execution?: Record<string, unknown> | null;
    attempts: number;
    repaired: boolean;
    retry_history: CopilotRetryStep[];
};