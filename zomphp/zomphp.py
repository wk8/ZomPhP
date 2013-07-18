#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import os
import logging

import backend
import utils

if os.path.exists('/etc/zomphp/zomphp_settings.py'):
    sys.path.append('/etc/zomphp')


def main():
    # argument processing
    parser = argparse.ArgumentParser(description='Detect your PHP dead code')
    parser.add_argument('--dir', dest='dir', metavar='dir_path',
                        type=str, nargs=1, default=None,
                        help='Make ZomPHP process that directory')
    parser.add_argument('--ignore-sub-dirs', dest='ignore_sub_dirs',
                        metavar='dir_path', type=str, nargs='+', default=[],
                        help='A directory path (or list of those) that won\'t '
                        'be processed (only makes sense when used with the '
                        '--dir option)')
    parser.add_argument('--files', dest='files', metavar='file_path',
                        type=str, nargs='+', default=[],
                        help='A file or list of files (given as absolute paths'
                        ') to have processed by ZomPHP')
    parser.add_argument('--strict', dest='strict', action='store_const',
                        const=True, default=False, help='If set to true, will'
                        ' guarantee that any function NOT marked is indeed '
                        'used, but might also yield more false negatives (this'
                        ' option should only be used if you have files '
                        'containing functions with the same name)')
    parser.add_argument('--path-translation', dest='path_translation',
                        metavar='local_path path_in_db', type=str, nargs='+',
                        default=[], help='A list of couples of paths to '
                        'translate (useful if running the code in a different '
                        'location than the one running the PHP code)')
    parser.add_argument('--logging-level', dest='logging_level', metavar='level',
                        type=str, nargs=1, default=None, help='A logging '
                        'level to override the one set in the settings file')
    args = parser.parse_args()

    # start the logger
    utils.set_logger()

    # some sanity checks
    def check_abs_path(path, option_name):
        # helper function, checks the paths are absolute, and translates them to real paths
        if not path:
            return path
        if isinstance(path, (tuple, list)):
            return [check_abs_path(p, option_name) for p in path]
        if os.path.isabs(path):
            return os.path.realpath(path)
        logging.error('The --%s option requires using absolute paths (you entered %s) exiting' % (option_name, path))
        sys.exit(1)
    if bool(args.dir) == bool(args.files):
        logging.error('You must specify exactly one of the --dir or --files options, exiting')
        sys.exit(1)
    args.dir = check_abs_path(args.dir, 'dir')
    args.files = check_abs_path(args.files, 'files')
    if args.ignore_sub_dirs:
        if args.dir:
            args.ignore_sub_dirs = check_abs_path(args.ignore_sub_dirs, 'ignore-sub-dirs')
        else:
            logging.warning('Ignoring the --ignore-sub-dirs option, that option can only be used together with the --dir option')
    translator = utils.PathTranslator.build_translator(args.path_translation)

    # down to work!
    bckend = backend.get_new_backend()

    if args.dir:
        bckend.process_directory(args.dir[0], strict=args.strict, ignore_sub_dirs=args.ignore_sub_dirs, translator=translator)
    else:
        # then it must be --files
        for fle in args.files:
            bckend.process_file(fle, args.strict, translator=translator)


if __name__ == '__main__':
    main()
