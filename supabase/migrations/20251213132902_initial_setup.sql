-- Enable pgvector extension
create extension if not exists vector;

-- Create documents table
create table if not exists documents (
  id uuid primary key,
  client_id text not null,
  content text not null,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  
  -- Embedding column (future proofing)
  embedding vector(1536)
);

-- Index for client_id for frequent filtering
create index if not exists idx_documents_client_id on documents(client_id);
