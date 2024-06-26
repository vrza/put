#!/usr/bin/env python3

import datetime
import functools
import math
import os
import shutil
import subprocess


class Editor:
    DEFAULT_EDITOR = 'vim'

    def __init__(self):
        if 'EDITOR' not in os.environ:
            os.environ['EDITOR'] = os.environ.get('VISUAL', self.DEFAULT_EDITOR)
        self.editorcmd = os.environ['EDITOR']

    def edit(self, target):
        # cmdstr = f"{self.editorcmd} {target}"
        # os.system(cmdstr)
        cmd = [self.editorcmd, target]
        process = subprocess.Popen(cmd, env=os.environ)
        process.wait()


class FileMetadata:
    def __init__(self, wd, path):
        self.basename = path
        self.name = os.path.join(wd, path)
        self.islink = os.path.islink(self.name)
        self.isbrokenlink = True if self.islink and not os.path.exists(os.readlink(self.name)) else False
        self.isdir = False if self.isbrokenlink else os.path.isdir(self.name)
        self.size = 0 if self.isbrokenlink else os.path.getsize(self.name)

    def modification_time(self):
        t = os.path.getmtime(self.name)
        return datetime.datetime.fromtimestamp(t)

    def render(self, maxnamelen):
        rendername = f"{self.basename}/" if self.isdir else self.basename
        name = f"{rendername}\t".expandtabs(maxnamelen + 2)
        size = '{:>10}'.format('N/A' if self.isbrokenlink else self.size)
        mtime = 'N/A' if self.isbrokenlink else self.modification_time().strftime("%Y-%m-%d %H:%M")
        return name + size + "  " + mtime


# TODO cache stats
def sizeof_fmt(num):
    """Human readable file size"""
    unit_list = list(zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 1, 1, 1]))
    if num > 1:
        exponent = min(int(math.log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024 ** exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{:.%sf} {}' % num_decimals
        return format_string.format(quotient, unit)
    if num == 0:
        return '0 bytes'
    if num == 1:
        return '1 byte'


class FileManager:
    def __init__(self, workdir):
        self.wd = workdir
        self.files = self.selected_files = None
        self.total = self.used = self.free = 0
        self.max_filename_len = self.total_size = self.selected_size = 0
        self.change_dir(workdir)

    def change_dir(self, workdir):
        self.wd = workdir
        self.refresh()

    def refresh(self):
        self.total, self.used, self.free = shutil.disk_usage(self.wd)

        # TODO different sorts
        #self.files = sorted([f for f in os.listdir(self.wd) if os.path.isfile(os.path.join(self.wd, f))])
        self.files = sorted([f for f in os.listdir(self.wd)])
        self.max_filename_len = max(list(map(lambda x: len(x), self.files))) if self.files else 12
        self.total_size = 0
        self.recalculate_total_files_size()

        self.selected_files = set()
        self.selected_size = 0

    def file_count(self):
        return len(self.files)

    def selected_count(self):
        return len(self.selected_files)

    def recalculate_total_files_size(self):
        self.total_size = self.recalculate_files_size(self.files)

    def recalculate_selected_files_size(self):
        self.selected_size = self.recalculate_files_size(self.selected_file_paths())

    def selected_file_paths(self):
        return list(map(lambda i: self.files[i], self.selected_files))

    def recalculate_files_size(self, files):
        return functools.reduce(lambda x, y: x + y, list(
            map(lambda x: FileMetadata(self.wd, x).size, files))) if files else 0

    def get_path(self, idx):
        return os.path.join(self.wd, self.files[idx])

    def select_file(self, idx):
        self.selected_files.add(idx)
        self.recalculate_selected_files_size()

    def unselect_file(self, idx):
        self.selected_files.remove(idx)
        self.recalculate_selected_files_size()

    def delete_selected_files(self):
        for idx in self.selected_files:
            os.unlink(self.get_path(idx))
        self.refresh()
