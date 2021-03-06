#!/usr/bin/python2
import sys
import itertools
import functools
import shlex
import urwid
import utility
from functools import partial


def search(iterable, predicate, key=(lambda x: x)):
    for item in iterable:
        if predicate(
            key( item )
        ):
            return item
    return None

def shift_iterable(iterable, offset, direction):
    if direction == 'forward':
        return itertools.islice(
            itertools.cycle(iterable), offset, offset + len(iterable)
        )
    else:
        new_offset = len(iterable) - offset - 1
        return itertools.islice(
            itertools.cycle(reversed(iterable)), new_offset, new_offset + len(iterable)
        )
    
class MappedEdit(urwid.Edit):
    def __init__(self, keymap={}, disabled=False,
                 *args, **kwargs):

        self.disabled = disabled
        self.keymap = dict(keymap)
        super(MappedEdit, self).__init__(*args, **kwargs)

    def keypress(self, size, key):
        if key in self.keymap:
            key = self.keymap[key]()
        if key and not self.disabled:
            super(MappedEdit, self).keypress(size, key)
        return key

    def start_editing(self):
        pass


class MappedWrap(urwid.AttrMap):
    def __init__(self, widget,
                 attrmap=None, focusmap=None,
                 keymap={}, selectable=True,
                 *args, **kwargs):
        
        cls = widget.__class__
        signals = urwid.signals._signals._supported[cls]
        for signal in signals:
            urwid.register_signal(MappedWrap, signal)


        self.__dict__['_widget'] = widget
        self.__dict__['keymap'] = dict(keymap)
        self.__dict__['_s'] = selectable

        super(MappedWrap, self).__init__(widget, attrmap, focusmap, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._widget, name)

    def __setattr__(self, name, value):
        if hasattr(MappedWrap, name):
            return getattr(MappedWrap, name).fset(self, value)
        else:
            return setattr(self._widget, name, value)

    def keypress(self, size, key):
        if hasattr(self._widget, 'keypress'):
            key = super(MappedWrap, self).keypress(size, key)
        if key in self.keymap:
            key = self.keymap[key]()
        return key

    def selectable(self):
        return self._s

    @property
    def attrmap(self):
        return self.attr_map

    @attrmap.setter
    def attrmap(self, value):
        if hasattr(value, 'items'):
            self.set_attr_map(value)
        else:
            self.set_attr_map({None: value})

    @property
    def focusmap(self):
        return self.focus_map

    @focusmap.setter
    def focusmap(self, value):
        self.set_focus_map(value)

    @property
    def base_widget(self):
        if hasattr(self._widget, 'base_widget'):
            return self._widget.base_widget
        return self._widget


class CommandFrameController(object):
    def __init__(self, command_frame, commands):
        self._frame = command_frame
        self._commands = dict(commands)

    def areyousure(self, yes, no):
        def no_func():
            no()
            self._frame.escape()

        def yes_func():
            yes()
            self._frame.escape()

        return (yes_func, no_func)
            
    def submit_command(self, data):
        if data.strip():
            try:
                parse_result = shlex.split(data)
            except ValueError:
                self._frame.change_status("Invalid command")
            else:
                func = parse_result[0]
                args = parse_result[1:]
                if func not in self._commands:
                    self._frame.change_status("Command not found")
                else:
                    try:   
                        self._commands[func](*args)
                    except TypeError:
                        # Too many arguments
                        self._frame.change_status("Wrong number of arguments")

    def start_editing(self, callback, completion_set):
        callback = callback or self.submit_command
        tab_through = {}

        def tab(widget, text):
            tab_through.clear()

        def complete():
            if not tab_through:
                text, hits = utility.complete(
                    completion_set,
                    self._frame.command_line_text
                )
                tab_through[text] = itertools.cycle(hits)
            else:
                text = tab_through.values()[0].next()

            self._frame.command_line_text = text
            self._frame.command_line_position = len(self._frame.command_line_text)

        def enter_command():
            t = self._frame.command_line_text
            self._frame.stop_editing()
            callback(t)

        def backspace():
            tab_through.clear()
            if self._frame.command_line_text == '':
                self._frame.stop_editing()

        return (tab, complete, enter_command, backspace)


class CommandFrame(urwid.Frame):
    def __init__(self, body, header=None, focus_part='body', commands={}):
        self.__controller = CommandFrameController(self, commands)

        if not hasattr(self, 'keymap'):
            self.keymap = {}

        command_line = urwid.Edit(multiline=False)
        self.command_line = MappedWrap(command_line)


        self.keymap[':'] = functools.partial(self.start_editing, callback=self.submit_command)


        super(CommandFrame, self).__init__(body, header, self.command_line, focus_part)

    def keypress(self, size, key):
        key = urwid.Frame.keypress(self, size, key)
        if key in self.keymap:
            self.keymap[key]()
        return key

    def escape(self):
        self.footer = self.command_line
        self.focus_position = 'body'
        
    def areyousure(self, text="Are you sure?", yes=(lambda: None), no=(lambda: None)):
        yes_func, no_func = self.__controller.areyousure(yes, no)

        ays_text = '%s [y/n]' % text

        maps = {
            'esc': no_func,
            'y': yes_func,
            'Y': yes_func,
            'n': no_func,
            'N': no_func,
        }

        widget = MappedWrap(
            urwid.Text(ays_text),
            keymap=maps
        )

        self.footer = widget
        self.focus_position = 'footer'

    def submit_command(self, data):
        self.__controller.submit_command(data)

    def stop_editing(self):
        self.command_line.set_caption('')
        self.command_line.set_edit_text('')
        self.focus_position = 'body'

    def start_editing(self, caption='> ', startText='', callback=None, completion_set=()):
        self.command_line.set_caption(caption)
        self.command_line.set_edit_text(startText)
        self.command_line.edit_pos = len(startText)
        self.footer = self.command_line
        self.focus_position = "footer"

        tab, complete, enter, backspace = self.controller.start_editing(callback, completion_set)
        def wrapped_complete():
            urwid.disconnect_signal(self.command_line, 'change', tab)
            complete()
            urwid.connect_signal(self.command_line, 'change', tab)

        urwid.connect_signal(self.command_line, 'change', tab)
        self.command_line.keymap['esc'] = self.stop_editing
        self.command_line.keymap['enter'] = enter
        self.command_line.keymap['tab'] = wrapped_complete
        self.command_line.keymap['backspace'] = backspace
        
    def change_status(self, stat):
        self.footer = urwid.Text(stat)

    @property
    def command_line_text(self):
        return self.command_line.edit_text

    @command_line_text.setter
    def command_line_text(self, value):
        self.command_line.set_edit_text(value)

    @property
    def command_line_position(self):
        return self.command_line.edit_pos

    @command_line_position.setter
    def command_line_position(self, value):
        self.command_line.edit_pos = value


class MappedList(urwid.ListBox):
    def __init__(self, body, keymap={}):
        self.scroll = utility.scroll(range(len(body))) \
            if len(body) != 0 else utility.scroll([0])
        self.keymap = dict(keymap)

        self.search_anchor = None

        self._searcher = search
        self._builder = shift_iterable

        super(MappedList, self).__init__(body)

    def keypress(self, size, key):
        if key not in ('up', 'down'):
            key = super(MappedList, self).keypress(size, key)
        if key in self.keymap:
            key = self.keymap[key]()
        elif key == 'up':
            self.shiftUp()
        elif key == 'down':
            self.shiftDown()
        return key

    def top(self):
        self.set_focus(0)

    def bottom(self):
        self.set_focus(len(self.body) - 1)

    def shiftDown(self, amount=1):
        if self.body.focus is not self.scroll(amount):
            self.focus_position = self.scroll()
            self.body[:] = self.body[:]
            urwid.emit_signal(self, 'shift')
        else:
            urwid.emit_signal(self, 'bottom')

    def shiftUp(self, amount=1):
        if self.body.focus is not self.scroll(-amount):
            self.focus_position = self.scroll()
            self.body[:] = self.body[:]
            urwid.emit_signal(self, 'shift')
        else:
            urwid.emit_signal(self,'top')

    def set(self, contents):
        self.body[:] = contents
        currentIndex = self.scroll()
        focusIndex = len(contents) - 1 \
            if len(contents) < currentIndex \
            else currentIndex
        self.scroll = utility.scroll(range(len(contents)), focusIndex)

    def set_focus(self, position):
        self.focus_position = position
        self.set_focus_valign('middle')
        self.body[:] = self.body[:]
        self.scroll = utility.scroll(range(len(self.body[:])), position)
        urwid.emit_signal(self, 'shift')

    def inc_search(self, predicate, direction, key=(lambda x: x)):
        start = self.search_anchor if self.search_anchor is not None else self.focus_position
        self.search_anchor = start

        # Selects the item from the enumerable
        wrapped_key = lambda x: key( x[1] )
        iterable = shift_iterable(
            tuple(enumerate(self.body[:])), 
            start, direction
        )

        rtrn = search(
            iterable,
            predicate,
            key=wrapped_key
        )
        if rtrn is None:
            self.set_focus(start)
        else:
            index, item = rtrn
            self.set_focus(index)
    
    def _search(self, iterable):
        return self._searcher(
            iterable,
        )

        
    def search(self, predicate, direction, start=None, key=(lambda x: x)):

        self.search_anchor = None
        search_start = self.focus_position if start is None else start

        wrapped_key = lambda x: key( x[1] )

        iterable = shift_iterable(
            tuple(enumerate(self.body[:])), 
            search_start,
            direction,
        )

        # start = self.focus_position if start is 
        self._searcher = partial(
            search,
            predicate=predicate,
            key=wrapped_key
        )

        self._builder = partial(
            shift_iterable,
            direction=direction
        )

        rtrn = self._search(iterable)

        if rtrn is None:
            return None
        else:
            # Return the index of the enumerate
            return rtrn[0]


    def next(self):
        current_position = self.focus_position + 1

        iterable = self._builder(
            tuple(enumerate(self.body[:])),
            current_position
        )

        rtrn = self._search(
            iterable
        )

        if rtrn is not None:
            self.set_focus(rtrn[0])
    
    def prev(self):
        current_position = len(self.body[:]) - self.focus_position 

        iterable = self._builder(
            tuple(reversed(tuple(enumerate(self.body[:])))),
            current_position, 
        )

        rtrn = self._search(
            iterable
        )

        if rtrn is not None:
            self.set_focus(rtrn[0])

    def isEmpty(self):
        return len(self.body[:]) == 0


class MappedPile(urwid.Pile):
    def __init__(self, widgets=[], focus_item=None,
                 constraint=(lambda x, y: y.selectable()), keymap={}):
        self.keymap = dict(keymap)
        self.constraint = constraint
        super(MappedPile, self).__init__(widgets, focus_item)

    def keypress(self, size, key):
        key = super(MappedPile, self).keypress(size, key)
        if key in self.keymap:
            key = self.keymap[key]()
        return key

    def top(self):
        for index in xrange(len(self.contents)):
            widget = self.contents[index][0]
            if self.constraint(index, widget):
                self.focus_position = index
                urwid.emit_signal(self, 'shift')
                return
    
    def bottom(self):
        for index in xrange(len(self.contents) - 1, -1, -1):
            widget = self.contents[index][0]
            if self.constraint(index, widget):
                self.focus_position = index
                urwid.emit_signal(self, 'shift')
                return

    def shiftDown(self, amount=1):
        try:
            nextIndex = (
                index for index, widget in
                enumerate([cont[0] for cont in self.contents])
                if index > self.focus_position
                and self.constraint(index, widget)
            ).next()
            self.focus_position = nextIndex
            urwid.emit_signal(self, 'shift')
        except StopIteration:
            urwid.emit_signal(self, 'bottom')

    def shiftUp(self, amount=1):
        try:
            nextIndex = (
                index for index, widget in
                utility.renumerate([cont[0] for cont in self.contents]) 
                if index < self.focus_position
                and self.constraint(index, widget)
            ).next()
            self.focus_position = nextIndex
            urwid.emit_signal(self, 'shift')
        except StopIteration:
            urwid.emit_signal(self, 'top')

    def selectable(self):
        return reduce(
            (lambda x, y: x | y),
            [self.constraint(index, widget[0]) for index, widget in enumerate(self.contents)]
        )

    def isEmpty(self):
        return len(self.contents) == 0

    def add(self, widget):
        self.contents.append((widget, self.options()))
        if len(self.contents) == 1:
            self.focus_position = 0

    def set(self, widgets):
        self.contents = [(widget, self.options()) for widget in widgets]


class TitledPile(MappedPile):
    def __init__(self, title=urwid.Text(''), widgets=[], *args, **kwargs):
        self.title = title
        widgets = [title] + widgets
        super(TitledPile, self).__init__(widgets, *args, **kwargs)
        if not self.isEmpty():
            self.focus_position = 1

    def shiftUp(self):
        if self.focus_position > 1:
            super(TitledPile, self).shiftUp()
        else:
            urwid.emit_signal(self, 'top')

    def isEmpty(self):
        return len(self.contents) == 1

    def add(self, widget):
        self.contents.append((widget, self.options()))
        if len(self.contents) == 2:
            self.focus_position = 1

    def set(self, widgets):
        super(TitledPile, self).set((self.title,) + tuple(widgets))
        if len(self.contents) >= 2:
            self.focus_position = 1

    def setTitle(self, widget):
        self.title = widget
        self.contents[0] = (widget, self.options())

urwid.register_signal(TitledPile, ('shift', 'bottom', 'top'))
urwid.register_signal(MappedPile, ('shift', 'bottom', 'top'))
urwid.register_signal(MappedList, ('shift', 'bottom', 'top'))
