from redisvl.schema import IndexSchema

LOG_INDEX_SCHEMA = {
    "index": {
        "name": "aegis_logs",
        "prefix": "log:",
        "storage_type": "hash",
    },
    "fields": [
        {
            "name": "log_id",
            "type": "tag",
        },
        {
            "name": "timestamp",
            "type": "numeric",
        },
        {
            "name": "content",
            "type": "text",
        },
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": 384,
                "algorithm": "hnsw",
                "distance_metric": "cosine",
            },
        },
        {
            "name": "soreness_areas",
            "type": "text",
        },
        {
            "name": "movements",
            "type": "text",
        },
        {
            "name": "readiness",
            "type": "tag",
        },
    ],
}


def get_index_schema() -> IndexSchema:
    return IndexSchema.from_dict(LOG_INDEX_SCHEMA)
