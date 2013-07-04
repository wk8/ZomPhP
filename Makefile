.PHONY: clean

.SILENT: check_root

install: check_root
	./bin/install_daemonize.sh
	./bin/install_xdebug.sh

start: check_root
	./bin/start_daemon.sh

check_root:
	./bin/check_root.sh
