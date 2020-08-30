#!/usr/bin/env python3

import os
import argparse

import put.ui.file_functions


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', nargs='?', default=os.getcwd())
    args = parser.parse_args()
    return args


def main():
    args = parse_arguments()
    put.ui.file_functions.FileFunctions(args.dir).main()


if __name__ == '__main__':
    main()
