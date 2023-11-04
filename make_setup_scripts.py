#!/usr/bin/env python

import os, stat

create_db_contents = """#!/bin/bash
if [ "$USER" != "postgres" ] ; then
	echo "提示：如果没有权限创建数据库或创建postgis扩展，请用postgres用户运行该脚本。"
fi

export PROJECT_RUNDIR=/vol/iceval
export DB_NAME=iceval
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=iceval

if [ -e ./bashrc ] ; then
	source ./bashrc
fi

# create databases
echo "Making database $DB_NAME"
if [ $DB_HOST != "localhost" ] ; then
  HOST_ARG="--host=$DB_HOST"
else
  HOST_ARG=""
fi
createdb $HOST_ARG --port=$DB_PORT --owner=$DB_USER $DB_NAME
psql --port=$DB_PORT $DB_NAME << EOF
  CREATE EXTENSION postgis;
  \q
EOF
"""

create_site_contents = """#!/bin/bash

export PROJECT_RUNDIR=/vol/iceval
export DB_NAME=iceval

if [ -e ./bashrc ] ; then
	source ./bashrc
fi

# create dirs
if [ ! -d $PROJECT_RUNDIR ] ; then
	echo "Please provide the running root dir [ $PROJECT_RUNDIR ]"
	exit 1
fi

echo "Making site's folders ..."
for folder in http/static log
do
    to_make=$PROJECT_RUNDIR/$folder
    echo "    Making dir $to_make"
    mkdir -p $to_make
done

# Migrate databases
echo "Migrating databases ..."
./manage.py migrate

# Create admin
echo "Creating admin user ..."
./manage.py createsuperuser

# Collect static files
echo "Collecting static files ..."
./manage.py collectstatic
"""

for fname, contents in [
    ("create_db", create_db_contents),
    ("create_site", create_site_contents),
]:
    print(f"Making script {fname}")
    with open(fname, 'w') as f:
        f.write(contents)
    os.chmod(fname, stat.S_IRWXU)
