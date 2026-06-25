import { apiPost } from "../../lib/api/client";
import type {
    ExecuteResponse,
    PlanResponse,
    ValidateResponse,
} from "../../types/query";

export type SqlRequest = {
    sql: string;
};

export function validateSql(payload: SqlRequest) {
    return apiPost<ValidateResponse, SqlRequest>("/query/validate?debug=true", payload);
}

export function planSql(payload: SqlRequest) {
    return apiPost<PlanResponse, SqlRequest>("/query/plan?debug=true", payload);
}

export function executeSql(payload: SqlRequest) {
    return apiPost<ExecuteResponse, SqlRequest>("/query/execute?debug=true", payload);
}