# -*- coding: utf-8 -*-

import logging
import sys
import traceback
import os

from zomphp_settings import LOG_FILE, LOG_LEVEL


def set_logger(level=None):
    '''
    Sets the right logger
    '''
    logger = logging.getLogger()
    if LOG_FILE:
        # otherwise nothing else to do
        log_level = getattr(logging, LOG_LEVEL if level is None else level, logging.INFO)
        logging.basicConfig(level=log_level)
        format = '[%(asctime)s]%(levelname)s: %(message)s'
        formatter = logging.Formatter(fmt=format)
        handler = logging.FileHandler(LOG_FILE)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)

        # also log any uncaught exception
        def hook(type, value, tb):
            logging.exception('Uncaught exception of type %s\n%s' % (type.__name__, ''.join(traceback.format_tb(tb))))
        sys.excepthook = hook


class PathTranslator(object):
    '''
    @see the --path-translation option in zomphp.py
    '''

    def __init__(self, paths_list):
        if len(paths_list) % 2:
            raise ValueError('You need to provide a list of pairs of path')
        self._glossary = {(s if s.endswith(os.sep) else (s + os.sep)): t for s, t in zip(paths_list[::2], paths_list[1::2])}

    def translate(self, path):
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
