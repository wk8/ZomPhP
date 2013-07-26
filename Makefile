LCK_FILE := /tmp/zomphp.pid
INSTALL_DIR := /usr/lib/zomphp
VENV_DIR_NAME := venv

ULIMIT_FILES := 64000

ROOT_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))


.PHONY: check_dependencies check_root check_venv clean install install_daemon remove_dir restart start status stop uninstall status

.SILENT: check_dependencies check_root check_venv start status stop

###########
# Install #
###########

install: check_root check_dependencies install_daemon
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
	sed 's/<INSTALL_DIR>/$(ESCAPED_INSTALL_DIR)/g' $(INSTALL_DIR)/zomphp/zomphp.init.d > /etc/init.d/zomphp
	chmod +x /etc/init.d/zomphp
	# Create the settings folder
	mkdir -p /etc/zomphp
	touch /etc/zomphp/__init__.py
	/bin/bash -c "[ -a '/etc/zomphp/zomphp_settings.py' ] || cp $(INSTALL_DIR)/zomphp/zomphp_settings.py.tpl /etc/zomphp/zomphp_settings.py"
	# Install virtualenv
	@make VENV_DIR_LOC=$(INSTALL_DIR) check_venv

# installs the venv if needed, otherwise does nothing
check_venv:
ifndef VENV_DIR_LOC
	$(eval VENV_DIR_LOC := $(ROOT_DIR))
endif
	$(eval VENV_DIR := $(VENV_DIR_LOC)/$(VENV_DIR_NAME))
	/bin/bash -c "[ -d $(VENV_DIR) ] || eval 'echo \"Creating the virtualenv in $(VENV_DIR) and installing the requirements\" && virtualenv $(VENV_DIR) --no-site-packages && $(VENV_DIR)/bin/pip install --upgrade -r $(ROOT_DIR)/requirements.txt'"

uninstall: check_root
	@echo "Uninstalling ZomPHP..."
	@make remove_dir
	rm -f /etc/init.d/zomphp
	rm -rf /etc/zomphp

remove_dir:
	rm -rf $(INSTALL_DIR)

check_dependencies:
	/bin/bash -c "which git &> /dev/null || eval 'echo \"You need to install git! (http://git-scm.com/book/en/Getting-Started-Installing-Git)\" && exit 1'"
	/bin/bash -c "which virtualenv &> /dev/null || eval 'echo \"You need to install virtualenv! (http://www.virtualenv.org)\" && exit 1'"


#####################
# Daemon management #
#####################

start: check_root check_venv
	echo "Starting ZomPHP!"
	$(eval OWNER := $(shell $(ROOT_DIR)/zomphp/daemon.py --get-owner))
	# Make sure the socket file is clean ,start the venv, then the daemon itself
	/bin/bash -c "rm -f /tmp/zomphp.socket" && source $(ROOT_DIR)/$(VENV_DIR_NAME)/bin/activate && daemonize -p $(LCK_FILE) -l $(LCK_FILE) -u $(OWNER) $(ROOT_DIR)/zomphp/daemon.py"

stop: check_root
	/bin/bash -c "make status &> /dev/null || eval 'echo \"ZomPHP is not running\" && exit 1'"
	echo "Stopping ZomPHP!"
	kill `cat $(LCK_FILE)` # FIXME: graceful stop

restart: stop start

status: check_root
	/bin/bash -c "ps -p `/bin/bash -c '[ -a $(LCK_FILE) ] && cat $(LCK_FILE) || echo 1'` -o command= | grep "zomphp/daemon.py" > /dev/null && echo \"ZomPHP appears to be running\" || eval 'echo \"ZomPHP is not running\" && exit 1'"

##########################
# Git Subtree Management #
##########################

SUBTREE_ARGS := --prefix=lib/vendor/PHP-Parser --squash PHP-Parser master
git_subtree_pull:
	@make _git_subtree GIT_SUBTREE_ACTION=pull

git_subtree_push:
	@make _git_subtree GIT_SUBTREE_ACTION=push

_git_subtree:
	git subtree ${GIT_SUBTREE_ACTION} ${SUBTREE_ARGS}


###########
# Helpers #
###########

check_root:
	/bin/bash -c "[[ `whoami` == 'root' ]] || eval 'echo \"You need to be root to run this script\" && exit 1'"

clean:
	find . -type f -name "*.pyc" -print0 -exec rm -f {} \;

clean_sockets: stop
	rm -f /tmp/zomphp*
