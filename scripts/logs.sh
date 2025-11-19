#!/bin/bash

SERVICE=${1:-all}

if [ "$SERVICE" = "all" ]; then
    docker-compose logs -f
elif [ "$SERVICE" = "worker" ]; then
    docker-compose logs -f agno_worker
elif [ "$SERVICE" = "scheduler" ]; then
    docker-compose logs -f agno_scheduler
elif [ "$SERVICE" = "api" ]; then
    docker-compose logs -f api
elif [ "$SERVICE" = "rabbitmq" ]; then
    docker-compose logs -f rabbitmq
elif [ "$SERVICE" = "postgres" ]; then
    docker-compose logs -f postgres
elif [ "$SERVICE" = "browserless" ]; then
    docker-compose logs -f browserless
elif [ "$SERVICE" = "grafana" ]; then
    docker-compose logs -f grafana
else
    echo "Usage: $0 {all|worker|scheduler|api|rabbitmq|postgres|browserless|grafana}"
fi

