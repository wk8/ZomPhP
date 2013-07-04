#!/bin/bash

# Starts the actual deamon (must be root)
# Meant to be called from the root dir (make start)

# we need the absolute path of the top repo, hence readlink, and the dirty hack for systems that don't have readlink -f (mainly for Mac OS X)
ROOTDIR=`readlink -f "$(dirname "$(dirname "$0")")" 2> /dev/null` || ROOTDIR=`pwd`

# get the owner's name
OWNER=`./daemon/get_daemon_owner.py`

LCK_FILE='/tmp/zomphp.pid'

COMMAND="daemonize -p $LCK_FILE -l $LCK_FILE -u $OWNER $ROOTDIR/daemon/zomphp.py"
$COMMAND || exit $?
