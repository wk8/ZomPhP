#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

import backend

if os.path.exists('/etc/zomphp/zomphp_settings.py'):
    sys.path.append('/etc/zomphp')


def main():
    # argument processing
    parser = argparse.ArgumentParser(description='Detect your PHP dead code')
    parser.add_argument('--dir', dest='dir', metavar='directory_path',
                        type=str, nargs=1, default=None,
                        help='Make ZomPHP process that directory')
    parser.add_argument('--files', dest='files', metavar='file_path',
                        type=str, nargs='+', default=None,
                        help='A file or list of files (given as absolute paths'
                        ') to have processed by ZomPHP')
    parser.add_argument('--strict', dest='strict', action='store_const',
                        const=True, default=False, help='If set to true, will'
                        ' guarantee that any function NOT marked is indeed '
                        'used, but might also yield more false negatives (this'
                        ' option should only be used if you have files '
                        'containing functions with the same name)')
    args = parser.parse_args()
    if bool(args.dir) == bool(args.files):
        print 'You must specify exactly one of the --dir or --files options'
        sys.exit(1)

    # down to work!
    bckend = backend.get_new_backend()

    if args.dir:
        bckend.process_directory(args.dir, args.strict)
    else:
        for fle in args.files:
            bckend.process_file(fle, args.strict)


if __name__ == '__main__':
    main()
