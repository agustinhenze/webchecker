SHELL := bash
.DEFAULT_GOAL := help

up: ## Create kafka and postgres containers + webchecker container used for testing
	@docker-compose up --no-recreate -d
	@# wait for kafka service to be ready
	@docker-compose exec kafka-1 /home/appuser/webchecker/kafka_is_ready.sh

down: ## Delete all containers
	@docker-compose down --remove-orphan

test: up ## Run the test cases
	@docker-compose exec webchecker python3 -m unittest discover tests

help:  ## Print list of Makefile targets
	@# Taken from https://github.com/spf13/hugo/blob/master/Makefile
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		cut -d ":" -f1- | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
