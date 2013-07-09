LCK_FILE := /tmp/zomphp.pid
INSTALL_DIR := /usr/lib/zomphp

ROOT_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

ULIMIT_FILES := 64000


.PHONY: check_git check_root clean install install_daemon remove_dir restart start status stop uninstall status

.SILENT: check_root status check_git

install: check_root check_git install_daemon
	@echo "Installing daemonize..."
	$(ROOT_DIR)/bin/install_daemonize.sh
	@echo "Installing xdebug..."
	$(ROOT_DIR)/bin/install_xdebug.sh

install_daemon: check_root
	@echo "Installing ZomPHP..."
	@make remove_dir
	git clone https://github.com/wk8/ZomPhP.git $(INSTALL_DIR)
	# Install the init.d script
	$(eval ESCAPED_INSTALL_DIR := $(shell echo $(INSTALL_DIR) | sed 's/\//\\\//g'))
	sed 's/<INSTALL_DIR>/$(ESCAPED_INSTALL_DIR)/g' $(INSTALL_DIR)/daemon/zomphp.init.d > /etc/init.d/zomphp
	chmod +x /etc/init.d/zomphp
	# Create the settings folder
	mkdir -p /etc/zomphp
	touch /etc/zomphp/__init__.py
	/bin/bash -c "[ -a '/etc/zomphp/settings.py' ] || cp $(INSTALL_DIR)/daemon/settings.py.tpl /etc/zomphp/settings.py"

uninstall: check_root
	@echo "Uninstalling ZomPHP..."
	@make remove_dir
	rm -f /etc/init.d/zomphp
	rm -rf /etc/zomphp

remove_dir:
	rm -rf $(INSTALL_DIR)

start: check_root
	@echo "Starting ZomPHP!"
	$(eval OWNER := $(shell $(ROOT_DIR)/daemon/zomphp.py --get-owner))
	# increase the ulimit for that user and start the whole thing!
	ulimit -n $(ULIMIT_FILES) $(OWNER) && daemonize -p $(LCK_FILE) -l $(LCK_FILE) -u $(OWNER) $(ROOT_DIR)/daemon/zomphp.py

stop: check_root
	@echo "Stopping ZomPHP!"
	/bin/bash -c "make status &> /dev/null || eval 'echo \"ZomPHP is not running\" && exit 1'"
	kill `cat $(LCK_FILE)` # FIXME: graceful stop

restart: stop start

status: check_root
	@/bin/bash -c "ps -p `/bin/bash -c '[ -a $(LCK_FILE) ] && cat $(LCK_FILE) || echo 1'` -o command= | grep zomphp.py > /dev/null && echo \"ZomPHP appears to be running\" || eval 'echo \"ZomPHP is not running\" && exit 1'"

check_root:
	@/bin/bash -c "[[ `whoami` == 'root' ]] || eval 'echo \"You need to be root to run this script\" && exit 1'"

check_git:
	@/bin/bash -c "which git &> /dev/null || eval 'echo \"You need to install git! (http://git-scm.com/book/en/Getting-Started-Installing-Git)\" && exit 1'"

clean:
	find . -type f -name "*.pyc" -print0 -exec rm -f {} \;
