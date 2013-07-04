#!/bin/bash

# Installs our modified version of xdebug

cd /tmp \
&& git clone https://github.com/wk8/xdebug.git \
&& cd xdebug \
&& git checkout zomphp \
&& git pull \
&& ./install_full.sh \
|| exit $?
