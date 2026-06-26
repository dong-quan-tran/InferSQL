import { API_BASE_URL, ApiError } from "../../lib/api/client";

export type DatasetIngestRequest = {
    name: string;
    path: string;
    description?: string;
    overwrite?: boolean;
};

export type DatasetIngestResponse = {
    name: string;
    row_count: number;
    source_path?: string | null;
    loaded_at?: string | null;
    description?: string | null;
};

async function parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();

    if (!response.ok) {
        throw new ApiError(
            `Request failed with status ${response.status}`,
            response.status,
            payload,
        );
    }

    return payload as T;
}

export async function ingestFromPath(
    payload: DatasetIngestRequest,
): Promise<DatasetIngestResponse> {
    const overwrite = payload.overwrite ? "true" : "false";

    const response = await fetch(
        `${API_BASE_URL}/catalog/ingest?overwrite=${overwrite}`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                name: payload.name,
                path: payload.path,
                description: payload.description || null,
            }),
        },
    );

    return parseResponse<DatasetIngestResponse>(response);
}

export type UploadDatasetRequest = {
    name: string;
    file: File;
    description?: string;
    overwrite?: boolean;
};

export async function uploadDataset(
    payload: UploadDatasetRequest,
): Promise<DatasetIngestResponse> {
    const overwrite = payload.overwrite ? "true" : "false";

    const formData = new FormData();
    formData.append("name", payload.name);
    formData.append("file", payload.file);

    if (payload.description?.trim()) {
        formData.append("description", payload.description.trim());
    }

    const response = await fetch(
        `${API_BASE_URL}/catalog/upload?overwrite=${overwrite}`,
        {
            method: "POST",
            body: formData,
        },
    );

    return parseResponse<DatasetIngestResponse>(response);
}