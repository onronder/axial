#!/bin/bash
set -e

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -U pip
pip install -r backend/requirements-test.txt
pip install pytest pytest-asyncio httpx

# Run tests
echo "Running tests..."
export PYTHONPATH=backend
export SUPABASE_URL="https://example.supabase.co"
export SUPABASE_SECRET_KEY="dummy_secret"
export SUPABASE_JWT_SECRET="dummy_jwt_secret"
export OPENAI_API_KEY="dummy_openai_key"
pytest backend/tests/unit/test_billing.py -v
