create or replace function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns setof documents
language plpgsql
as $$
begin
  return query
  select *
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
