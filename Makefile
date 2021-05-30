CMD := docker-compose

up:
	$(CMD) up -d
build:
	$(CMD) build
init:
	$(CMD) up -d --build
	$(CMD) exec python mkdir ./app/log
	$(CMD) exec python chmod 777 ./app/log
	$(CMD) exec python flask initdb
	$(CMD) exec python chmod 666 ./app/sqlite_db
stop:
	$(CMD) stop
down:
	$(CMD) down --remove-orphans
restart:
	@make down
	@make up
destroy:
	$(CMD) down --rmi all --volumes --remove-orphans
destroy-volumes:
	$(CMD) down --volumes --remove-orphans
ps:
	$(CMD) ps
logs:
	$(CMD) logs
logs-watch:
	$(CMD) logs --follow
log-python:
	$(CMD) logs python
log-python-watch:
	$(CMD) logs --follow python
python:
	$(CMD) exec python bash
run:
	$(CMD) exec python flask run -h 0.0.0.0 -p 5000
