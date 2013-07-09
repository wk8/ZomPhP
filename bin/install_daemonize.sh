#!/bin/bash

# This script installs deamon (hhttp://software.clapper.org/daemonize/) if not present (need to be root)

function install_daemonize
{
	cd /tmp \
	&& rm -rf daemonize \
	&& git clone https://github.com/bmc/daemonize.git \
	&& cd daemonize \
	&& ./configure \
	&& make \
	&& make install \
	|| exit $?
}

which daemonize &> /dev/null || install_daemonize
