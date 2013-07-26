#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import argparse
from twisted.internet import reactor, protocol

if os.path.exists('/etc/zomphp/zomphp_settings.py'):
    sys.path.append('/etc/zomphp')

from utils import set_logger
from zomphp_settings import ZOMPHP_DEAMON_OWNER
from constants import SOCKET_PATH
from backend import get_new_backend


class ZomPHPServer(protocol.Protocol):
    def __init__(self, factory):
        logging.debug('Starting new server')
        self._factory = factory

    def dataReceived(self, data):
        self._factory.report_data(data)


class ZomPHPServerFactory(protocol.Factory):
    def __init__(self):
        logging.debug('Initializing new factory')
        self._backend = get_new_backend()

    def buildProtocol(self, addr):
        return ZomPHPServer(self)

    def report_data(self, data):
        for item in data.split('\n'):
            if item:
                self._backend.process_raw_data(item)


class ZomPHPApp(object):

    def run(self):
        factory = ZomPHPServerFactory()
        reactor.listenUNIX(SOCKET_PATH, factory)
        reactor.run()


def main():
    # argument processing
    parser = argparse.ArgumentParser(description='Detect your PHP dead code')
    parser.add_argument('--get-owner', dest='get_owner', action='store_const',
                        const=True, default=False, help='Outputs the deamon\'s owner'
                        ' as set in the configuration, then exits')
    args = parser.parse_args()

    if args.get_owner:
        print ZOMPHP_DEAMON_OWNER if ZOMPHP_DEAMON_OWNER else 'root'
    else:
        # normal operation
        set_logger()
        app = ZomPHPApp()
        app.run()


if __name__ == '__main__':
    main()
