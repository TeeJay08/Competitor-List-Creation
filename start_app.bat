@echo off
echo Starting Competitor List API Server...
start cmd /k "python -m uvicorn api:app --reload --port 8000"

echo Starting React User Interface...
cd frontend
start cmd /k "npm run dev"

echo.
echo Both servers are starting up!
echo The React App will be available at http://localhost:5173
echo The API Backend is running at http://localhost:8000
echo.
