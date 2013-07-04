.PHONY: clean

.SILENT: check_root

all:

start: check_root
	./bin/start_daemon.sh

install_daemonize:
	./bin/install_daemonize.sh

check_root:
	./bin/check_root.sh
