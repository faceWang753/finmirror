.PHONY: generate demo review-app test lint typecheck build verify

generate:
	finmirror generate

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

verify: generate review-app test lint typecheck build
