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


class PathTranslator(object):
    '''
    @see the --path-translation option in zomphp.py
    '''

    def __init__(self, paths_list):
        if len(path_lists) % 2:
            raise ValueError('You need to provide a list of pairs of path')
        self._glossary = {s: t for s, t in zip(path_lists[::2], path_lists[1::2])}

    def translate(path):
        '''
        Translates an absolute path
        '''
        for s in self._glossary:
            if path.startswith(s):
                return os.path.join(self._glossary[s], path[len(s):])
        return path

    @classmethod
    def build_translator(cls, paths_list):
        if paths_list:
            return cls(paths_list)
        return None
