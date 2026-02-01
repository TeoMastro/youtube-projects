# WooCommerce RAG Chatbot - Database Setup

## Quick Start Guide for New Installation

This README contains the complete SQL setup for a fresh Supabase installation to support your WooCommerce RAG chatbot.

---

## Prerequisites

- Supabase project created
- Access to Supabase SQL Editor
- n8n instance ready (Version 2.2.6+)

---

## Step 1: Run the Complete SQL Setup

Copy and paste the **entire script below** into your Supabase SQL Editor and click **RUN**.

```sql
-- ============================================
-- WOOCOMMERCE RAG CHATBOT - COMPLETE SETUP
-- Run this entire script in Supabase SQL Editor
-- ============================================

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create the product_embeddings table
CREATE TABLE product_embeddings (
  id bigserial PRIMARY KEY,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
  embedding vector(1536), -- 1536 dimensions for text-embedding-3-small
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Step 3: Add generated product_id column for easier querying and upserts
ALTER TABLE product_embeddings 
ADD COLUMN product_id text 
GENERATED ALWAYS AS (metadata->>'product_id') STORED;

-- Step 4: Create unique index on product_id (enables upserts)
CREATE UNIQUE INDEX product_embeddings_product_id_unique 
ON product_embeddings(product_id);

-- Step 5: Create vector similarity index (for fast similarity search)
CREATE INDEX product_embeddings_embedding_idx 
ON product_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 6: Create metadata indexes (for filtering by category, etc.)
CREATE INDEX product_embeddings_metadata_idx 
ON product_embeddings USING gin (metadata);

CREATE INDEX product_embeddings_metadata_category_idx 
ON product_embeddings USING gin ((metadata -> 'category'));

CREATE INDEX product_embeddings_metadata_stock_idx 
ON product_embeddings USING btree ((metadata->>'stock_status'));

-- Step 7: Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Create trigger for auto-updating updated_at
CREATE TRIGGER update_product_embeddings_updated_at 
BEFORE UPDATE ON product_embeddings 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 9: Create the match_documents function (required by n8n)
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(1536),
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'::jsonb
) 
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    product_embeddings.id,
    product_embeddings.content,
    product_embeddings.metadata,
    1 - (product_embeddings.embedding <=> query_embedding) AS similarity
  FROM product_embeddings
  WHERE (filter = '{}'::jsonb OR metadata @> filter)
  ORDER BY product_embeddings.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Step 10: Create hybrid search function (optional, for text + vector search)
CREATE OR REPLACE FUNCTION match_documents_hybrid (
  query_embedding vector(1536),
  query_text text DEFAULT '',
  match_count int DEFAULT 5,
  filter jsonb DEFAULT '{}'::jsonb
) 
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    product_embeddings.id,
    product_embeddings.content,
    product_embeddings.metadata,
    1 - (product_embeddings.embedding <=> query_embedding) AS similarity
  FROM product_embeddings
  WHERE (filter = '{}'::jsonb OR metadata @> filter)
    AND (query_text = '' OR content ILIKE '%' || query_text || '%')
  ORDER BY 
    (1 - (product_embeddings.embedding <=> query_embedding)) DESC
  LIMIT match_count;
END;
$$;

-- Step 11: Grant necessary permissions
GRANT ALL ON product_embeddings TO postgres, anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE product_embeddings_id_seq TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_documents TO postgres, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION match_documents_hybrid TO postgres, anon, authenticated, service_role;

-- ============================================
-- SETUP COMPLETE!
-- ============================================

-- Verification queries (run these to verify setup):
SELECT 'pgvector extension installed' AS status 
WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector');

SELECT 'product_embeddings table created' AS status 
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'product_embeddings');

SELECT 'match_documents function created' AS status 
WHERE EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'match_documents');

SELECT 
  tablename,
  indexname,
  indexdef
FROM pg_indexes 
WHERE tablename = 'product_embeddings'
ORDER BY indexname;
```

---

## Step 2: Verify Installation

After running the script, verify everything is set up correctly:

```sql
-- Check if pgvector extension is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check table structure
SELECT 
  column_name, 
  data_type, 
  is_nullable,
  column_default
FROM information_schema.columns 
WHERE table_name = 'product_embeddings'
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'product_embeddings';

-- Check functions
SELECT routine_name, routine_type
FROM information_schema.routines 
WHERE routine_name LIKE 'match_documents%';

-- Check permissions
SELECT 
  grantee, 
  privilege_type 
FROM information_schema.table_privileges 
WHERE table_name = 'product_embeddings';
```

**Expected Results:**
- ✅ pgvector extension exists
- ✅ Table has 7 columns: id, content, metadata, embedding, created_at, updated_at, product_id
- ✅ 5 indexes created
- ✅ 2 functions: match_documents and match_documents_hybrid
- ✅ Permissions granted to postgres, anon, authenticated, service_role

---

## Table Structure

### Columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigserial | Primary key, auto-increment |
| `content` | text | Full product text for display |
| `metadata` | jsonb | Product details (name, price, category, etc.) |
| `embedding` | vector(1536) | Vector representation for similarity search |
| `created_at` | timestamp | When the product was first added |
| `updated_at` | timestamp | Last update time (auto-updated) |
| `product_id` | text | Generated column from metadata, used for upserts |

### Metadata Structure

Each product's metadata contains:

```json
{
  "product_id": "305",
  "name": "Audio-Technica ATH-G1WL",
  "price": "179",
  "category": "Electronics, Headsets",
  "category_ids": [41, 132],
  "sku": "HEAD-029",
  "url": "https://yourstore.com/product/...",
  "stock_status": "instock",
  "image_url": "https://...",
  "last_modified": "2026-01-25T09:44:31"
}
```

---

## Important Notes

### Embedding Model
This setup uses **text-embedding-3-small** (1536 dimensions). If you want to use a different model:

**For text-embedding-3-large (3072 dimensions):**
```sql
-- Change vector dimension in table
ALTER TABLE product_embeddings ALTER COLUMN embedding TYPE vector(3072);

-- Update both functions to use vector(3072)
-- You'll need to drop and recreate the functions with the new dimension
```

### Upsert Behavior
The unique index on `product_id` enables automatic upserts in n8n:
- If a product with the same `product_id` exists → **UPDATE**
- If not → **INSERT**

This prevents duplicate products in your database.

---

## Sample Queries

### Find all products
```sql
SELECT 
  product_id,
  metadata->>'name' AS name,
  metadata->>'price' AS price,
  metadata->>'category' AS category
FROM product_embeddings
LIMIT 10;
```

### Find products by category
```sql
SELECT 
  metadata->>'name' AS name,
  metadata->>'category' AS category,
  metadata->>'price' AS price
FROM product_embeddings
WHERE metadata->>'category' LIKE '%Electronics%';
```

### Find out-of-stock products
```sql
SELECT 
  metadata->>'name' AS name,
  metadata->>'stock_status' AS status
FROM product_embeddings
WHERE metadata->>'stock_status' = 'outofstock';
```

### Count products per category
```sql
SELECT 
  metadata->>'category' AS category,
  COUNT(*) AS product_count
FROM product_embeddings
GROUP BY metadata->>'category'
ORDER BY product_count DESC;
```

### Test similarity search (after you have data)
```sql
-- This is what your chatbot will use
SELECT * FROM match_documents(
  '[0.1, 0.2, ...]'::vector(1536),  -- Your query embedding
  5,  -- Return top 5 results
  '{}'::jsonb  -- No filter
);
```

---

## Next Steps

After running this SQL setup:

1. ✅ **Import the n8n workflow** (`woocommerce_sync_workflow_fixed.json`)
2. ✅ **Configure credentials** in n8n:
   - WooCommerce API (Consumer Key + Secret)
   - Supabase API (Project URL + Service Role Key)
   - OpenAI API (API Key)
3. ✅ **Run the Manual Trigger** to import all products (one-time)
4. ✅ **Activate the Schedule Trigger** for daily updates

---

## Troubleshooting

### Error: "type vector does not exist"
**Solution:** pgvector extension not installed. Run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Error: "function match_documents does not exist"
**Solution:** Function not created. Re-run Step 9 from the main script.

### Error: "permission denied"
**Solution:** Grants not applied. Re-run Step 11 from the main script.

### Products not upserting (creating duplicates)
**Solution:** Unique index missing. Run:
```sql
CREATE UNIQUE INDEX IF NOT EXISTS product_embeddings_product_id_unique 
ON product_embeddings(product_id);
```

---

## Performance Optimization

### For Large Stores (1000+ products)

Increase the IVFFlat lists parameter:
```sql
-- Drop old index
DROP INDEX IF EXISTS product_embeddings_embedding_idx;

-- Create new index with more lists
CREATE INDEX product_embeddings_embedding_idx 
ON product_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);  -- Increase from 100 to 200 for better performance
```

**Rule of thumb:** 
- < 1000 products: `lists = 100`
- 1000-10000 products: `lists = 200`
- 10000+ products: `lists = 500`

---

## Maintenance

### Vacuum the table periodically
```sql
VACUUM ANALYZE product_embeddings;
```

### Check table size
```sql
SELECT 
  pg_size_pretty(pg_total_relation_size('product_embeddings')) AS total_size,
  pg_size_pretty(pg_relation_size('product_embeddings')) AS table_size,
  pg_size_pretty(pg_indexes_size('product_embeddings')) AS indexes_size;
```

### Delete all data (start fresh)
```sql
TRUNCATE product_embeddings RESTART IDENTITY;
```

---

## Support

- **n8n Documentation:** https://docs.n8n.io
- **Supabase Vector Docs:** https://supabase.com/docs/guides/ai/vector-columns
- **pgvector GitHub:** https://github.com/pgvector/pgvector
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings

---

## License

This setup is provided as-is for WooCommerce RAG chatbot implementation.
