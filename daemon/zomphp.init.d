#!/bin/bash
# Starts and stops ZomPHP

INSTALL_DIR=<INSTALL_DIR>

case "$1" in
'start' | 'stop' | 'restart' | 'status')
	make -C $INSTALL_DIR "$1" || exit $?
;;

*)
	echo "Usage: $0 {start|stop|restart|status}"
	exit 1
esac
