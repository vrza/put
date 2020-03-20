#!/usr/bin/env python3
import collections
import datetime
import functools
import os
import argparse
import shutil
import signal
import subprocess
import urwid
from math import log

class MainLoop(urwid.MainLoop):
  def exit_signal_handler(self, frame):
    raise urwid.ExitMainLoop()

  signal.signal(signal.SIGINT, exit_signal_handler)
  signal.signal(signal.SIGTSTP, exit_signal_handler)


class SelectableText(urwid.Text):
  def selectable(self):
    return True

  def keypress(self, size, key):
    return key


class ViListBox(urwid.ListBox):
  # Catch key presses in box and pass them as arrow keys
  def keypress(self, size, key):
    if key == 'j':
      key = 'down'
    elif key == 'k':
      key = 'up'
    elif key == 'h':
      key = 'left'
    elif key == 'l':
      key = 'right'
    return super(ViListBox, self).keypress(size, key)


class Editor:
  def __init__(self):
    DEFAULT_EDITOR = 'vim'
    if 'EDITOR' not in os.environ:
      os.environ['EDITOR'] = os.environ.get('VISUAL', DEFAULT_EDITOR)
    self.editorcmd = os.environ['EDITOR']
  
  def edit(self, target):
      #cmdstr = f"{self.editorcmd} {target}"
      #os.system(cmdstr)
      cmd = [self.editorcmd, target]
      process = subprocess.Popen(cmd, env=os.environ)
      process.wait()


class FileMetadata:
  def __init__(self, wd, path):
    self.basename = path 
    self.name = os.path.join(wd, path)
    self.size = os.path.getsize(self.name)

  def modification_time(self):
    t = os.path.getmtime(self.name)
    return datetime.datetime.fromtimestamp(t)

  def render(self, maxnamelen):
    name = f"{self.basename}\t".expandtabs(maxnamelen + 2)
    size = '{:>10}'.format(self.size)
    mtime = self.modification_time().strftime("%Y-%m-%d %H:%M")
    return name + size + "  " + mtime
 
# TODO cache stats
class FileManager:
  def __init__(self, workdir):
    self.wd = workdir
    self.total, self.used, self.free = shutil.disk_usage(self.wd)

    # TODO different sorts
    self.files = sorted([f for f in os.listdir(self.wd) if os.path.isfile(os.path.join(self.wd, f))])
    self.maxfilenamelen = max(list(map(lambda x: len(x), self.files))) if self.files else 12
    self.recalculate_total_files_size()

    self.selectedfiles = set()
    self.selectedsize = 0

  def filecount(self):
    return len(self.files)

  def selectedcount(self):
    return len(self.selectedfiles)

  def recalculate_total_files_size(self):
    self.totalsize = functools.reduce(lambda x, y: x + y, list(map(lambda x: os.path.getsize(os.path.join(self.wd, x)), self.files))) if self.files else 0

  def recalculate_selected_files_size(self):
    self.selectedsize = functools.reduce(lambda x, y: x + y, list(map(lambda i: os.path.getsize(os.path.join(self.wd, self.files[i])), self.selectedfiles))) if self.selectedfiles else 0

  def get_path(self, idx):
    return os.path.join(self.wd, self.files[idx])

  def select_file(self, idx):
    self.selectedfiles.add(idx)
    self.recalculate_selected_files_size()

  def unselect_file(self, idx):
    self.selectedfiles.remove(idx)
    self.recalculate_selected_files_size()

  def sizeof_fmt(self, num):
    """Human readable file size"""
    unit_list = list(zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 1, 1, 1]))
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{:.%sf} {}' % (num_decimals)
        return format_string.format(quotient, unit)
    if num == 0:
        return '0 bytes'
    if num == 1:
        return '1 byte'

class FileFunctions(urwid.WidgetPlaceholder):
  app_name = u'put'
  app_version = '0.5'
  app_title = f'{app_name} {app_version}'
  module_title = u"File Functions"
  # TODO override with custom palette from config file
  palette = [
    ('body', 'light gray', 'black'),
    ('file', 'light gray', 'black'),
    ('file_sel', 'white', 'black'),
    ('focus', 'black', 'dark red', 'standout'),
    ('focus_sel', 'white', 'dark red', 'standout'),
    ('head', 'light gray', 'dark blue', 'standout'),
    ('blue', 'light gray', 'dark blue'),
    ('foot', 'light gray', 'black'),
    ('key', 'black', 'white'),
    ('title', 'white', 'black', 'bold'),
    ('columns', 'white', 'dark green', 'bold')
  ]
  lines_unicode = {
    "tlcorner": u'┌',
    "tline": u'─',
    "lline": u'│',
    "trcorner": u'┐',
    "blcorner": u'└',
    "rline": u'│',
    "bline": u'─',
    "brcorner": u'┘',
    "lconnector": u'├',
    "rconnector": u'┤'
  }
  lines_7bit = {
    "tlcorner": u'+',
    "tline": u'-',
    "lline": u'|',
    "trcorner": u'+',
    "blcorner": u'+',
    "rline": u'|',
    "bline": u'-',
    "brcorner": u'+',
    "lconnector": u'+',
    "rconnector": u'+'
  }
  l = lines_unicode
  #l = lines_7bit

  def metamapper(self, x):
    return urwid.AttrMap(SelectableText(FileMetadata(self.fm.wd, x).render(self.fm.maxfilenamelen)), attr_map='file', focus_map='focus')

  def __init__(self, wd):
    self.editor = Editor()
    self.fm = FileManager(wd)
    self.metacontent = list(map(self.metamapper, self.fm.files))
    self.appname_line = urwid.Text(self.app_title, 'left')

    self.module_fill = urwid.SolidFill(self.l.get("tline", u'─'))
    self.module_line = urwid.Text(self.module_title, 'center')
    self.module_overlay = urwid.Overlay(self.module_line, self.module_fill, 'center', len(self.module_title), 'top', 'pack')

    self.path_line = urwid.AttrWrap(urwid.Text(f"Path={self.fm.wd}", 'left'), 'body')
    # TODO grid?
    self.column_titles = urwid.AttrWrap(urwid.Text('Name\t      Size  Last Modified'.expandtabs(self.fm.maxfilenamelen + 2)), 'columns')
    self.header = urwid.Pile([self.appname_line,
                              (1, self.module_overlay),
                              self.path_line,
                              self.column_titles])
    self.listwalker = urwid.SimpleFocusListWalker(self.metacontent)
    self.listbox = ViListBox(self.listwalker)
    self.menu = urwid.Text(
[('key', 'C'), "opy ", ('key', 'M'), "ove c", ('key', 'O'), "mp ", ('key', 'F'), "ind ", ('key', 'R'), "ename ", ('key', 'D'), "elete view/", ('key', 'E'), "dit ", ('key', 'P'), "ermissions o", ('key', 'W'), "ner", os.linesep,
('key', 'S'), "ort ", ('key', 'H'), "elp ", ('key', "◄┘"), "=SELECT ", ('key', "F1"), "=UNselect ", ('key', "F2"), "=alt dir lst ", ('key', "F3"), "=other menu ", ('key', "ESC"), "=", ('key', 'Q'), "uit PU Tools", os.linesep,
('key', "F8"), "=directory LIST argument  ", ('key', "F9"), "=file SELECTion argument  ", ('key', "F10"), "=change path"], 'center')
    self.menubox = urwid.LineBox(self.menu, title='', title_align='center',
                                 tlcorner=self.l.get("lconnector", u'├'),
                                 tline=self.l.get("tline", u'─'),
                                 lline=self.l.get("lline", u'│'),
                                 trcorner=self.l.get("rconnector", u'┤'),
                                 blcorner=self.l.get("blcorner", u'└'),
                                 rline=self.l.get("rline", u'│'),
                                 bline=self.l.get("bline", u'─'),
                                 brcorner=self.l.get("brcorner", u'┘'))
    self.update_statbox()
    self.footer = urwid.Pile([self.statbox, self.menubox])
    self.view = urwid.Frame(
        body = urwid.AttrWrap(self.listbox, 'body'),
        header = urwid.AttrWrap(self.header, 'blue'),
        footer = urwid.AttrWrap(self.footer, 'blue'))

  def render_size(self, size):
    return '{:>8}'.format(self.fm.sizeof_fmt(size))

  # TODO extend LineBox to provide update functionality?
  def update_statbox(self):
    stat_listed = urwid.Text('{:>24}'.format(f'{self.fm.filecount()} files LISTed   = ') + f'{self.render_size(self.fm.totalsize)}', 'left')
    stat_selected = urwid.Text('{:>24}'.format(f'{self.fm.selectedcount()} files SELECTed = ') + f'{self.render_size(self.fm.selectedsize)}', 'left')
    stat_subdir = urwid.Text('{:>24}'.format(f'{self.fm.filecount()} files in sub-dir = ') + f'{self.render_size(self.fm.totalsize)}', 'left')
    stat_available = urwid.Text('{:>24}'.format(f'Available on volume = ') + f'{self.render_size(self.fm.free)}', 'left')

    stat_pile_left = urwid.Pile([stat_listed, stat_selected])
    stat_pile_right = urwid.Pile([stat_subdir, stat_available])
    stats = urwid.Columns([stat_pile_left, stat_pile_right])

    colorstats = urwid.AttrWrap(stats, 'foot')
    self.statbox = urwid.LineBox(colorstats, title='', title_align='center',
                                 tlcorner=self.l.get("tlcorner", u'┌'),
                                 tline=self.l.get("tline", u'─'),
                                 lline=self.l.get("lline", u'│'),
                                 trcorner=self.l.get("trcorner", u'┐'),
                                 blcorner='',
                                 rline=self.l.get("rline", u'│'),
                                 bline='',
                                 brcorner='')

  def update_footer(self):
    self.update_statbox()
    self.footer = urwid.Pile([self.statbox, self.menubox])
    self.view.set_footer(urwid.AttrWrap(self.footer, 'blue'))

  def focus_file_path(self):
    _focus_widget, idx = self.listwalker.get_focus()
    path = self.fm.get_path(idx)
    return path

  def select(self):
    _focus_widget, idx = self.listwalker.get_focus()
    self.fm.select_file(idx)
    self.listwalker[idx] = urwid.AttrMap(SelectableText(FileMetadata(self.fm.wd, self.fm.files[idx]).render(self.fm.maxfilenamelen)), attr_map='file_sel', focus_map='focus_sel')
    self.listwalker.set_focus((idx + 1) % len(self.listwalker))
    self.update_footer()

  def unselect(self):
    _focus_widget, idx = self.listwalker.get_focus()
    if idx not in self.fm.selectedfiles:
      return
    self.fm.unselect_file(idx)
    self.listwalker[idx] = urwid.AttrMap(SelectableText(FileMetadata(self.fm.wd, self.fm.files[idx]).render(self.fm.maxfilenamelen)), attr_map='file', focus_map='focus')
    self.listwalker.set_focus((idx + 1) % len(self.listwalker))
    self.update_footer()

  # TODO extend mainloop to update widgets?
  def main(self):
    self.loop = urwid.MainLoop(self.view, self.palette,
            unhandled_input=self.unhandled_input)
    self.loop.run()

  def invoke_editor(self):
      self.loop.screen.clear()
      self.editor.edit(self.focus_file_path())
      self.loop.screen.clear()

  def unhandled_input(self, k):
    # update display of focus directory
    if k in ('q','Q', 'esc'):
      print(self.fm.selectedfiles)
      raise urwid.ExitMainLoop()
    # TODO move this to custom ListBox class
    if k in ('e','E'):
      self.invoke_editor()
      return
    if k in ('enter'):
      self.select()
      return
    if k in ('f1'):
      self.unselect()
      return

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('dir', nargs='?', default=os.getcwd())
  args = parser.parse_args()
  FileFunctions(args.dir).main()

if __name__ == '__main__':
  main()
