const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

export class ApiError extends Error {
    status: number;
    payload: unknown;

    constructor(message: string, status: number, payload: unknown) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.payload = payload;
    }
}

async function parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();

    if (!response.ok) {
        const message =
            typeof payload === "object" &&
                payload !== null &&
                "error" in payload &&
                typeof (payload as any).error?.message === "string"
                ? (payload as any).error.message
                : `Request failed with status ${response.status}`;

        throw new ApiError(message, response.status, payload);
    }

    return payload as T;
}

export async function apiGet<T>(path: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
    });

    return parseResponse<T>(response);
}

export async function apiPost<TResponse, TBody>(
    path: string,
    body: TBody,
): Promise<TResponse> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify(body),
    });

    return parseResponse<TResponse>(response);
}

export { API_BASE_URL };