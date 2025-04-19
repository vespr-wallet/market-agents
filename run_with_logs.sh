#!/bin/bash

# Set the port (use the provided PORT env var or default to 8000)
export PORT="${PORT:-8000}"

echo "Starting FastAPI server on port ${PORT}..."
echo "Log streaming available at: http://localhost:${PORT}/logs"
echo "Log viewer available at: http://localhost:${PORT}/log-viewer"
echo ""
echo "Press Ctrl+C to stop the server"

# Run the server
python3 main.py api 