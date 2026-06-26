import { apiGet } from "../../lib/api/client";
import type {
    CatalogDatasetDetailResponse,
    CatalogDatasetsResponse,
} from "../../types/catalog";

export function fetchDatasets() {
    return apiGet<CatalogDatasetsResponse>("/catalog/datasets");
}

export function fetchDatasetDetail(name: string) {
    return apiGet<CatalogDatasetDetailResponse>(
        `/catalog/datasets/${encodeURIComponent(name)}`,
    );
}