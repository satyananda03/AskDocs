run:
	uv run python run.py

run-dev:
	uv run python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000