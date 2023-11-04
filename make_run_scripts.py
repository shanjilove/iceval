#!/usr/bin/env python

import os, stat

run_site_contents = """#!/usr/bin/env bash

TODAY=`date +"%Y%m%d"`
export PROJECT_RUNDIR="/vol/iceval"
export PROJECT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
export PROJECT_PORT=8000
export CELERY_TASK_DEFAULT_QUEUE=iceval
export CELERY_NCPU=`grep -c ^processor /proc/cpuinfo`

if [ -e ./bashrc ] ; then
	source ./bashrc
fi

#celery purge -A iceval -f

keep_alive "gunicorn iceval.wsgi -c iceval/confs/gunicorn.conf.py" "gunicorn iceval.wsgi -c iceval/confs/gunicorn.conf.py" "$PROJECT_DIR" "$PROJECT_RUNDIR/log/log.run.${TODAY}.log"

worker_log="$PROJECT_RUNDIR/log/celery.worker.$TODAY.log"
keep_alive "celery -A iceval worker -Q $CELERY_TASK_DEFAULT_QUEUE -l info -c $CELERY_NCPU" "celery -A iceval worker -Q $CELERY_TASK_DEFAULT_QUEUE -l info" "$PROJECT_DIR" "$worker_log"

beat_log="$PROJECT_RUNDIR/log/celery.beat.$TODAY.log"
beat_pid="$PROJECT_RUNDIR/log/celery.beat.pid"
beat_sch="$PROJECT_RUNDIR/log/celery.beat.schedule"
keep_alive "celery -A iceval beat -l info --pidfile=$beat_pid -s $beat_sch --scheduler django_celery_beat.schedulers:DatabaseScheduler" "celery -A iceval beat" "$PROJECT_DIR" "$beat_log"

exit 0
"""

stop_site_contents = """#!/usr/bin/env bash

export PROJECT_RUNDIR="/vol/iceval"
export PROJECT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
export PROJECT_PORT=8000

if [ -e ./bashrc ] ; then
	source ./bashrc
fi

PKILL "gunicorn iceval.wsgi -c iceval/confs/gunicorn.conf.py"
PKILL "celery -A iceval worker"
PKILL "celery -A iceval beat"

beat_pid="$PROJECT_RUNDIR/log/celery.beat.pid"
rm -f $beat_pid

exit 0
"""

for fname, contents in [
    ("run_site", run_site_contents),
    ("stop_site", stop_site_contents),
]:
    print(f"Making script {fname}")
    with open(fname, 'w') as f:
        f.write(contents)
    os.chmod(fname, stat.S_IRWXU)

