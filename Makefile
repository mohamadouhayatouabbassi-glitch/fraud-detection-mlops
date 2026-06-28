.PHONY: help install lint format typecheck test test-cov data train serve docker-build docker-up clean

PYTHON ?= python
PORT   ?= 8000

help:
	@echo "Targets:"
	@echo "  install       Install package + dev deps via uv"
	@echo "  lint          Ruff + black --check"
	@echo "  format        Black + ruff --fix"
	@echo "  typecheck     mypy"
	@echo "  test          pytest (unit + integration)"
	@echo "  test-cov      pytest with coverage report"
	@echo "  data          Generate synthetic train/test data"
	@echo "  train         Train model end-to-end"
	@echo "  serve         Run FastAPI locally on PORT=$(PORT)"
	@echo "  docker-build  Build docker image"
	@echo "  docker-up     Up docker-compose"
	@echo "  clean         Remove caches + artifacts"

install:
	uv venv --python 3.11
	uv pip install -e ".[dev]"

lint:
	ruff check src tests
	black --check src tests

format:
	ruff check --fix src tests
	black src tests

typecheck:
	mypy src

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml

data:
	$(PYTHON) -m fraud_detection.cli generate-data --n-rows 200000 --fraud-rate 0.012

train:
	$(PYTHON) -m fraud_detection.cli train

serve:
	uvicorn fraud_detection.api.main:app --host 0.0.0.0 --port $(PORT) --reload

docker-build:
	docker build -t fraud-detection-api:latest .

docker-up:
	docker compose up --build

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
