#!/bin/bash

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

container_name=`docker ps --format '{{.Names}}' | grep "db"`
container_count=`echo $container_name | wc -l`
fname=db_dump_$(date +"%Y-%m-%d_%H_%M_%S")

#find all old backups and rename them.
old_bkp_files=`ls -l /tmp/db_dump_*.gz`
old_bkp_list=`echo $old_bkp_files | wc -l`

#run this part only if old backups exist
if [ "$old_bkp_list" -gt "0" ];
then
    echo $(red Found old backups..)
    for filename in /tmp/db_dump_*.gz; do
        echo $(red $filename)
        mv $filename $filename.bkp
    done
fi

#start backup
source .env
echo $(green Backing up $container_name...)
if [ "$container_count" -eq "1" ];
then
  docker exec -t $container_name pg_dumpall -c -U "$POSTGRES_USER" | gzip > /tmp/$fname.gz
  echo $(green Backup complete.)
fi

#clean up
echo $(green cleaning up....)
echo $(red Deleting ALL old backups...)
rm -rf /tmp/db_dump_*.gz.bkp
echo $(green Done.)
echo $(green New backup file is /tmp/$fname.gz)
