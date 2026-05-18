.PHONY: install run generate-schema lint lint-fix format

install:
	pip install -r requirements.txt
	pip install pre-commit ruff
	pre-commit install
	.venv/bin/python -m patchright install chromium

run:
	.venv/bin/python main.py

generate-schema:
	.venv/bin/python -m config > playquery.schema.json

lint:
	.venv/bin/ruff check .

lint-fix:
	.venv/bin/ruff check . --fix

format:
	.venv/bin/ruff format .
