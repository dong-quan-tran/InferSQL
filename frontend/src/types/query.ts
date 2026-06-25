export type QueryDebug = {
    request_id?: string;
    total_ms?: number;
    stage?: string;
    engine?: string | null;
    error_origin?: string | null;
    features?: string[];
};

export type QueryErrorDetail = {
    type: string;
    code: string;
    message: string;
    status_code: number;
    request_id?: string;
    debug?: QueryDebug;
};

export type ErrorResponse = {
    error: QueryErrorDetail;
};

export type ValidateResponse = {
    sql: string;
    normalized_sql: string;
    is_valid: boolean;
    query_type: string;
    errors: string[];
    tables: string[];
    columns: string[];
    has_where: boolean;
    has_group_by: boolean;
    has_order_by: boolean;
    has_limit: boolean;
    debug?: QueryDebug;
};

export type PlanNode = {
    node_type: string;
    details?: Record<string, unknown>;
    children?: PlanNode[];
};

export type PlanResponse = {
    sql: string;
    normalized_sql: string;
    engine?: string | null;
    steps?: string[];
    logical_plan?: PlanNode | null;
    physical_plan?: PlanNode | null;
    debug?: QueryDebug;
};

export type ExecuteRow = Record<string, unknown>;

export type ExecuteResponse = {
    sql: string;
    normalized_sql: string;
    row_count: number;
    columns: string[];
    rows: ExecuteRow[];
    logical_plan?: PlanNode | null;
    physical_plan?: PlanNode | null;
    debug?: QueryDebug;
};