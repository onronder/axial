-- Migration: Relational Document Architecture

-- 0. Cleanup old schema (Playground mode: Wipe data to apply new structure)
drop table if exists documents cascade;
drop table if exists document_chunks cascade;

-- 1. Create 'documents' table (Parent Metadata)
create type source_type_enum as enum ('file', 'web', 'drive');

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null, -- Mapped to auth.users in real app, keeping generic for now
    title text not null,
    source_type source_type_enum not null,
    source_url text, -- Optional, for web/drive
    created_at timestamptz default now(),
    metadata jsonb default '{}'::jsonb
);

-- Index for fast user filtering
create index idx_documents_user_id on documents(user_id);

-- 2. Create 'document_chunks' table (Vector Storage)
create table if not exists document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid references documents(id) on delete cascade not null,
    content text not null,
    embedding vector(1536),
    chunk_index int,
    created_at timestamptz default now()
);

-- Index for vector search (HNSW)
create index on document_chunks using hnsw (embedding vector_cosine_ops);
-- Index for joining with documents
create index idx_document_chunks_document_id on document_chunks(document_id);

-- 3. Enable RLS
alter table documents enable row level security;
alter table document_chunks enable row level security;

-- Policy: Users can only see their own documents
create policy "Users can crud their own documents"
  on documents for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Policy: Chunks access inherits from parent document
-- Note: Simplified RLS. Ideally check document_id ownership. 
-- For performance in simple app, we might rely on the join in the RPC or explicit user_id on chunks too.
-- Let's stick to the secure pattern: Chunks don't have user_id efficiently without join. 
-- But for writing, we can check. For selecting, we often use the RPC.
-- To allow simple select:
create policy "Users can select own chunks via parent"
  on document_chunks for select
  using (
    exists (
      select 1 from documents
      where documents.id = document_chunks.document_id
      and documents.user_id = auth.uid()
    )
  );

-- 4. Update Matching RPC
create or replace function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_user_id uuid
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float,
  source_type source_type_enum,
  document_id uuid
)
language plpgsql
as $$
begin
  return query (
    select
      document_chunks.id,
      document_chunks.content,
      documents.metadata, -- Return parent metadata
      1 - (document_chunks.embedding <=> query_embedding) as similarity,
      documents.source_type,
      documents.id as document_id
    from document_chunks
    join documents on document_chunks.document_id = documents.id
    where 1 - (document_chunks.embedding <=> query_embedding) > match_threshold
    and documents.user_id = filter_user_id
    order by document_chunks.embedding <=> query_embedding
    limit match_count
  );
end;
$$;
