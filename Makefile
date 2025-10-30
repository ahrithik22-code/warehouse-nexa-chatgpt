.PHONY: dev migrate seed test build up

dev:
python manage.py runserver

migrate:
python manage.py migrate

seed:
python manage.py loaddata seed.json

test:
pytest

build:
docker build -t warehouse-app .

up:
docker-compose up --build
