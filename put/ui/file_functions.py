#!/usr/bin/env python3

import os
import signal

import urwid

import put.fm.file_manager


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


def render_size(size):
    return '{:>8}'.format(put.fm.file_manager.sizeof_fmt(size))


class FileFunctions(urwid.WidgetPlaceholder):
    app_name = u'put'
    app_version = '0.5'
    app_title = f'{app_name} {app_version}'
    module_title = u"File Functions"
    # TODO override with custom palette from config file
    palette_blue = [
        ('body', 'light gray', 'black'),
        ('file', 'light gray', 'black'),
        ('file_sel', 'white', 'black'),
        ('file_focus', 'black', 'dark red', 'standout'),
        ('file_focus_sel', 'white', 'dark red', 'standout'),
        ('dir', 'light blue', 'black'),
        ('dir_sel', 'light cyan', 'black'),
        ('dir_focus', 'light blue', 'dark red', 'standout'),
        ('dir_focus_sel', 'light cyan', 'dark red', 'standout'),
        ('broken_link', 'white', 'light red'),
        ('broken_link_sel', 'dark blue', 'light red'),
        ('broken_link_focus', 'black', 'dark red', 'standout'),
        ('broken_link_focus_sel', 'white', 'dark red', 'standout'),
        ('head', 'light gray', 'dark blue', 'standout'),
        ('main', 'light gray', 'dark blue'),
        ('foot', 'light gray', 'black'),
        ('key', 'black', 'white'),
        ('title', 'white', 'black', 'bold'),
        ('columns', 'white', 'dark green', 'bold')
    ]
    palette = palette_blue
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

    # l = lines_7bit

    def metamapper(self, x):
        metadata = put.fm.file_manager.FileMetadata(self.fm.wd, x)
        attrmap = 'dir' if metadata.isdir else 'file'
        focusmap = 'dir_focus' if metadata.isdir else 'file_focus'
        return urwid.AttrMap(SelectableText(metadata.render(self.fm.max_filename_len)), attr_map=attrmap, focus_map=focusmap)


    def __init__(self, wd):
        super(FileFunctions, self).__init__(self)
        self.editor = put.fm.file_manager.Editor()
        self.fm = put.fm.file_manager.FileManager(wd)
        self.metacontent = list(map(self.metamapper, self.fm.files))
        self.appname_line = urwid.Text(self.app_title, 'left')

        self.module_fill = urwid.SolidFill(self.l.get("tline", u'─'))
        self.module_line = urwid.Text(self.module_title, 'center')
        self.module_overlay = urwid.Overlay(self.module_line, self.module_fill, 'center', len(self.module_title), 'top',
                                            'pack')

        self.path_line = urwid.AttrWrap(urwid.Text(f"Path={self.fm.wd}", 'left'), 'body')
        # TODO grid?
        self.column_titles = urwid.AttrWrap(
            urwid.Text('Name\t      Size  Last Modified'.expandtabs(self.fm.max_filename_len + 2)), 'columns')
        self.header = urwid.Pile([self.appname_line,
                                  (1, self.module_overlay),
                                  self.path_line,
                                  self.column_titles])
        self.listwalker = urwid.SimpleFocusListWalker(self.metacontent)
        self.listbox = ViListBox(self.listwalker)
        self.menu = urwid.Text(
            [('key', 'C'), "opy ", ('key', 'M'), "ove c", ('key', 'O'), "mp ", ('key', 'F'), "ind ", ('key', 'R'),
             "ename ", ('key', 'D'), "elete view/", ('key', 'E'), "dit ", ('key', 'P'), "ermissions o", ('key', 'W'),
             "ner", os.linesep,
             ('key', 'S'), "ort ", ('key', 'H'), "elp ", ('key', "◄┘"), "=SELECT ", ('key', "F1"), "=UNselect ",
             ('key', "F2"), "=alt dir lst ", ('key', "F3"), "=other menu ", ('key', "ESC"), "=", ('key', 'Q'),
             "uit PU Tools", os.linesep,
             ('key', "F8"), "=directory LIST argument  ", ('key', "F9"), "=file SELECTion argument  ", ('key', "F10"),
             "=change path"], 'center')
        self.menubox = urwid.LineBox(self.menu, title='', title_align='center',
                                     tlcorner=self.l.get("lconnector", u'├'),
                                     tline=self.l.get("tline", u'─'),
                                     lline=self.l.get("lline", u'│'),
                                     trcorner=self.l.get("rconnector", u'┤'),
                                     blcorner=self.l.get("blcorner", u'└'),
                                     rline=self.l.get("rline", u'│'),
                                     bline=self.l.get("bline", u'─'),
                                     brcorner=self.l.get("brcorner", u'┘'))
        self.statbox = None
        self.update_statbox()
        self.footer = urwid.Pile([self.statbox, self.menubox])
        self.view = urwid.Frame(
            body=urwid.AttrWrap(self.listbox, 'body'),
            header=urwid.AttrWrap(self.header, 'main'),
            footer=urwid.AttrWrap(self.footer, 'main'))

        self.loop = urwid.MainLoop(self.view, self.palette,
                                   unhandled_input=self.unhandled_input)

    # TODO extend LineBox to provide update functionality?
    def update_statbox(self):
        stat_listed = urwid.Text(
            '{:>24}'.format(f'{self.fm.file_count()} files LISTed   = ') + f'{render_size(self.fm.total_size)}',
            'left')
        stat_selected = urwid.Text('{:>24}'.format(
            f'{self.fm.selected_count()} files SELECTed = ') + f'{render_size(self.fm.selected_size)}', 'left')
        stat_subdir = urwid.Text(
            '{:>24}'.format(f'{self.fm.file_count()} files in sub-dir = ') + f'{render_size(self.fm.total_size)}',
            'left')
        stat_available = urwid.Text('{:>24}'.format(f'Available on volume = ') + f'{render_size(self.fm.free)}',
                                    'left')

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
        self.view.set_footer(urwid.AttrMap(self.footer, 'main'))

    def focus_file_path(self):
        _focus_widget, idx = self.listwalker.get_focus()
        path = self.fm.get_path(idx)
        return path

    def select(self):
        _focus_widget, idx = self.listwalker.get_focus()
        self.fm.select_file(idx)
        metadata = put.fm.file_manager.FileMetadata(self.fm.wd, self.fm.files[idx])
        attrmap = 'broken_link_sel' if metadata.isbrokenlink else ('dir_sel' if metadata.isdir else 'file_sel')
        focusmap = 'broken_link_focus_sel' if metadata.isbrokenlink else ('dir_focus_sel' if metadata.isdir else 'file_focus_sel')
        self.listwalker[idx] = urwid.AttrMap(
            SelectableText(metadata.render(self.fm.max_filename_len)),
            attr_map=attrmap, focus_map=focusmap)
        self.listwalker.set_focus((idx + 1) % len(self.listwalker))
        self.update_footer()

    def unselect(self):
        _focus_widget, idx = self.  listwalker.get_focus()
        if idx not in self.fm.selected_files:
            return
        self.fm.unselect_file(idx)
        metadata = put.fm.file_manager.FileMetadata(self.fm.wd, self.fm.files[idx])
        filename = metadata.render(self.fm.max_filename_len)
        attrmap = 'broken_link' if metadata.isbrokenlink else ('dir' if metadata.isdir else 'file')
        focusmap = 'broken_link_focus' if metadata.isbrokenlink else ('dir_focus' if metadata.isdir else 'file_focus')
        self.listwalker[idx] = urwid.AttrMap(
            SelectableText(filename),
            attr_map=attrmap, focus_map=focusmap)
        self.listwalker.set_focus((idx + 1) % len(self.listwalker))
        self.update_footer()

    # TODO extend mainloop to update widgets?
    def main(self):
        self.loop.run()

    def delete_selected_files(self):
        # TODO ask for confirmation
        self.fm.delete_selected_files()

    def invoke_editor(self):
        self.loop.screen.clear()
        self.editor.edit(self.focus_file_path())
        self.loop.screen.clear()

    def unhandled_input(self, k):
        # update display of focus directory
        if k in ('q', 'Q', 'esc'):
            print(self.fm.selected_files)
            raise urwid.ExitMainLoop()
        # TODO move this to custom ListBox class
        if k in ('d', 'D'):
            self.delete_selected_files()
            return
        if k in ('e', 'E'):
            self.invoke_editor()
            return
        if k in ('enter'):
            self.select()
            return
        if k in ('f1'):
            self.unselect()
            return
