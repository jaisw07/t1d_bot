from pymilvus import DataType, FieldSchema, CollectionSchema

def get_milvus_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
        FieldSchema(name="dense_embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name="sparse_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source_document", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="collection", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="topic", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="contains_dosage", dtype=DataType.BOOL),
        FieldSchema(name="contains_recommendation", dtype=DataType.BOOL),
        FieldSchema(name="start_page", dtype=DataType.INT64),
        FieldSchema(name="section_title", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="keywords", dtype=DataType.VARCHAR, max_length=1024)
    ]
    return CollectionSchema(fields=fields, description="T1D Knowledge Base Collection")
