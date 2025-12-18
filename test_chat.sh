#!/bin/bash
# Test the Chat RAG Endpoint

API_KEY="default-insecure-key"
URL="http://localhost:8000/api/v1/chat"

echo "Testing Chat RAG Endpoint..."
echo "Query: 'What is deepmind?'"

curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $API_KEY" \
  -d '{
    "query": "What is deepmind?",
    "model": "gpt-4o"
  }' | json_pp

echo -e "\n\nDone."
