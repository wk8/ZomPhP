#!/bin/bash

# This script installs deamon (hhttp://software.clapper.org/daemonize/) if not present (need to be root)

function install_daemonize
{
	cd /tmp \
	&& rm -rf daemonize \
	&& git clone git@github.com:bmc/daemonize.git \
	&& cd daemonize \
	&& ./configure \
	&& make \
	&& make install
}

# you need git!
which git &> /dev/null || eval 'echo "You need to install git! (http://git-scm.com/book/en/Getting-Started-Installing-Git)" && exit 1'
which daemonize &> /dev/null || install_daemonize
