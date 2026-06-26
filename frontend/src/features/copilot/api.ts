import { apiPost } from "../../lib/api/client";
import type {
    CopilotQueryRequest,
    CopilotQueryResponse,
} from "../../types/copilot";

export function runCopilotQuery(payload: CopilotQueryRequest) {
    return apiPost<CopilotQueryResponse, CopilotQueryRequest>(
        "/copilot/query",
        payload,
    );
}