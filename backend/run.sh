#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p data/chroma

# Run the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
