env ?= dev

.DEFAULT_GOAL:=help

ifeq ($(filter $(env),dev prod),)
  $(error the env variable is invalid. Must be one of <prod|dev>)
endif

COMPOSE_FILES_PATH := -f docker-compose.yml -f docker-$(env).yml

.PHONY: build test up up-detach down nuke restart test diagrams deploy logs ssh format help

build: ## This builds the images
	docker-compose $(COMPOSE_FILES_PATH) build

up: build ## This brings up the app
	docker-compose $(COMPOSE_FILES_PATH) up

up-detach: build ## This brings up the app and detaches the shell from the logs
	docker-compose $(COMPOSE_FILES_PATH) up -d

down: ## This takes down the app
	docker-compose $(COMPOSE_FILES_PATH) down

nuke: ## This removes all the volumes as well as taking down the app
	docker-compose $(COMPOSE_FILES_PATH) down -v

flush:
	docker exec src_web_1 python3 manage.py flush --no-input

initialize:
	docker exec src-web-1 python3 manage.py loaddata data/demo

restart: down up ## This restarts the app

test: down up-detach ## This runs the unit tests
	docker exec src-web-1 pip install pytest-django
	docker exec src-web-1 pytest --ds=meals.settings --junitxml=./testresult.xml
	docker-compose $(COMPOSE_FILES_PATH) down

test-coverage: down up-detach ## Generates a code coverage report
	docker exec src-web-1 coverage run manage.py test
	docker exec src-web-1 coverage report
	docker exec src-web-1 coverage html
	docker-compose $(COMPOSE_FILES_PATH) down

diagrams: down up-detach ## This creates uml diagrams of the models
	docker exec src-web-1 python manage.py graph_models -a -g -o generated/docs/diagrams/models-uml.png
	docker-compose $(COMPOSE_FILES_PATH) down

logs: ## This cats the logs from the django app
	sudo cat `docker inspect --format='{{.LogPath}}' src_web_1`

nginx1-21:
	docker pull nginx:1.21.6

backup-db:
	./db_backup.sh

deploy: nginx1-21 backup-db down up-detach ## This deploys the app in detached mode with a build

ssh: ## This docker execs you in to the web container
	bash ssh.sh

format: down up-detach ## Black and isort the entire repo
	docker exec src-web-1 autoflake -r --in-place .
	docker exec src-web-1 isort -rc . --skip-glob "**/*migrations/**"
	docker exec src-web-1 black . --line-length 95 --exclude \.*migrations
	docker-compose $(COMPOSE_FILES_PATH) down

help: ## This is the help dialog
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m env=<dev|prod> default: dev\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
