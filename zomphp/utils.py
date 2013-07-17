# -*- coding: utf-8 -*-

import logging
import sys
import threading
import traceback

from zomphp_settings import LOG_FILE, LOG_LEVEL


def enum(*enums):
    '''
    Implements enums (only exists in versions >= 3.4)
    '''
    return type('Enum', (), {e: e for e in enums})


def set_logger():
    '''
    Sets the right logger
    '''
    logger = logging.getLogger()
    if LOG_FILE:
        # otherwise nothing else to do
        log_level = getattr(logging, LOG_LEVEL, logging.INFO)
        logging.basicConfig(level=log_level)
        format = '[%(asctime)s]%(levelname)s:PID %(process)s:Thread %(threadName)s: %(message)s'
        formatter = logging.Formatter(fmt=format)
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)

        # also log any uncaught exception
        def hook(type, value, tb):
            logging.exception('Uncaught exception of type %s in thread %s: %s\n%s' % (type.__name__, threading.current_thread().name, str(value), ''.join(traceback.format_tb(tb))))
        sys.excepthook = hook
