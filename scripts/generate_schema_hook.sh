#!/usr/bin/env bash
# Pre-commit hook: regenerate playquery.schema.json and enforce it is staged.
set -e

.venv/bin/python -m search_engine.config > playquery.schema.json

# Compare the generated file against the staged (index) version.
# git show :file returns empty if the file is absent from the index (e.g. git rm'd
# or never added), which correctly triggers the failure path.
staged_content=$(git show :playquery.schema.json 2>/dev/null || echo "")
generated_content=$(cat playquery.schema.json)

if [ "$staged_content" != "$generated_content" ]; then
    echo ""
    echo "  playquery.schema.json was regenerated and differs from the staged version."
    echo "  Stage it before committing:"
    echo ""
    echo "      git add playquery.schema.json"
    echo ""
    exit 1
fi
