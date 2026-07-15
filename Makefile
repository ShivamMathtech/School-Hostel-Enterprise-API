install:
	python -m pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

seed:
	python -m scripts.seed

test:
	pytest

lint:
	ruff check .
