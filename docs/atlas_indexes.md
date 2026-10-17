# Atlas Index Definitions

Document the exact index JSON here. Indexes are created via Atlas UI (or Admin API if available).
See docs/decisions.md for verification status of creation method.

## 1. Vector Search Index (`vector_index`)

Applied to collection: `chunks`

```json
{
  "name": "vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 384,
        "similarity": "cosine"
      },
      {
        "type": "filter",
        "path": "brand"
      },
      {
        "type": "filter",
        "path": "model"
      },
      {
        "type": "filter",
        "path": "manual_id"
      }
    ]
  }
}
```

## 2. Atlas Search Index (BM25, `bm25_index`)

Applied to collection: `chunks`

```json
{
  "name": "bm25_index",
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": {
        "type": "string",
        "analyzer": "lucene.english"
      },
      "brand": {
        "type": "string"
      },
      "model": {
        "type": "string"
      },
      "manual_id": {
        "type": "string"
      },
      "section": {
        "type": "string"
      },
      "page": {
        "type": "number"
      }
    }
  }
}
```

## Creation Status
- [ ] vector_index created on Atlas UI
- [ ] bm25_index created on Atlas UI
- [ ] Both tested with sample queries
- [ ] Results logged in docs/decisions.md
