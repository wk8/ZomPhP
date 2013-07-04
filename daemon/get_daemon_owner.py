#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO wkpo venv?

from settings import ZOMPHP_DEAMON_OWNER

print ZOMPHP_DEAMON_OWNER if ZOMPHP_DEAMON_OWNER else 'root'
