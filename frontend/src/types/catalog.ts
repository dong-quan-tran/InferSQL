export type CatalogColumn = {
    name: string;
    type?: string | null;
    description?: string | null;
};

export type CatalogDataset = {
    name: string;
    description?: string | null;
    row_count?: number | null;
    source_path?: string | null;
    loaded_at?: string | null;
    columns?: CatalogColumn[];
    sample_rows?: Record<string, unknown>[];
};

export type CatalogDatasetsResponse = {
    datasets?: CatalogDataset[];
};

export type CatalogDatasetDetailResponse = CatalogDataset;