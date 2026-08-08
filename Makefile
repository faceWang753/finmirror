.PHONY: generate assurance demo review-app test lint typecheck build verify

generate:
	finmirror generate

assurance:
	finmirror assure-evaluator

demo:
	finmirror demo

review-app:
	python scripts/build_review_app.py

test:
	python -m pytest

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy

build:
	python -m build

verify: generate assurance review-app test lint typecheck build
