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
pip install -r backend/requirements-test.txt > /dev/null 2>&1

# Run tests
echo "Running All Backend Unit Tests..."
export PYTHONPATH=backend
export SUPABASE_URL="https://example.supabase.co"
export SUPABASE_SECRET_KEY="dummy_secret"
export SUPABASE_JWT_SECRET="dummy_jwt_secret"
export OPENAI_API_KEY="dummy_openai_key"

# Run all tests in backend/tests/unit
# Using -n auto if pytest-xdist is available would be faster, but let's stick to simple execution
pytest backend/tests/unit -v
