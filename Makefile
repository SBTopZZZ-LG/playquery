.PHONY: install run generate-schema

install:
	pip install -r requirements.txt

run:
	.venv/bin/python main.py

generate-schema:
	.venv/bin/python -m search_engine.config > playquery.schema.json
