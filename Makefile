up:
	docker-compose up -d
build:
	docker-compose build
init:
	docker-compose up -d --build
	docker-compose exec python mkdir ./app/log
	docker-compose exec python chmod 777 ./app/log
	docker-compose exec python flask initdb
	docker-compose exec python chmod 666 ./app/sqlite_db
stop:
	docker-compose stop
down:
	docker-compose down --remove-orphans
restart:
	@make down
	@make up
destroy:
	docker-compose down --rmi all --volumes --remove-orphans
destroy-volumes:
	docker-compose down --volumes --remove-orphans
ps:
	docker-compose ps
logs:
	docker-compose logs
logs-watch:
	docker-compose logs --follow
log-python:
	docker-compose logs python
log-python-watch:
	docker-compose logs --follow python
exec:
	docker-compose exec python bash
run:
	docker-compose exec python flask run -h 0.0.0.0 -p 5000
