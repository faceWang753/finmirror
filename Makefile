.PHONY: generate demo test lint typecheck build verify

generate:
	finmirror generate

demo:
	finmirror demo

test:
	python -m pytest

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy

build:
	python -m build

verify: generate test lint typecheck build

