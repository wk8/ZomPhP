#!/bin/bash

# Installs our modified version of xdebug

cd /tmp \
&& rm -rf xdebug \
&& git clone https://github.com/wk8/xdebug.git \
&& cd xdebug \
&& git pull \
&& ./install_full.sh \
|| exit $?

# FIXME: add the relevant lines to the php.ini files
