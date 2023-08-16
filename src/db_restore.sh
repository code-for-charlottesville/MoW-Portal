#!/bin/bash

container_name=`docker ps --format '{{.Names}}' | grep "db"`
container_count=`echo $container_name | wc -l`

# Color
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function red {
    printf "${RED}$@${NC}\n"
}

function green {
    printf "${GREEN}$@${NC}\n"
}

function usage {
    echo "      "
    echo $(red Dont forget to include the path and filename)
    echo $(red example: $0 /tmp/db_dump_2022-04-29_13_50_19.gz)
    echo "      "
    exit 1
}

if [ "$container_count" -eq "1" ];
then
  source .env

  if [ $# -ne 1 ];
    then
      usage
  else
    if [ -f $1 ];
    then
      echo $(green Starting backup...)
      gunzip < $1 | docker exec -i $container_name psql -U "$POSTGRES_USER" -d postgres > /tmp/log.txt
      echo $(green Restore complete. Verify log file in /tmp/log.)
    else
      echo $(red File not found. Restore not done.)
    fi
  fi
else
  echo $(red You have more than one container running.)
fi
