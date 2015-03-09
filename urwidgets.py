#!/usr/bin/python2
import urwid
import sys
import traceback
import pyparsing as pp
import itertools


class MappedText(urwid.AttrMap):
    def __init__(self, text,
                 attrmap=None, mapfocus=None,
                 **kwargs):
        self.textWidget = urwid.Text(text)
        super(MappedText, self).__init__(self.textWidget, attrmap, mapfocus)


class CommandFrame(urwid.Frame):
    argument = pp.Or((pp.Word(pp.printables), pp.QuotedString("'")))
    command = pp.Word(pp.alphas)
    commandLine = command + pp.ZeroOrMore(argument)
    functions = {}

    def __init__(self, body=None, header=None, focus_part='body'):
        self.editing = False
        self.edit = None
        urwid.Frame.__init__(self, body, header, self.edit, focus_part)

    def keypress(self, size, key):
        key = urwid.Frame.keypress(self, size, key)
        if key:
            if self.editing:
                if key == 'esc':
                    self.stopEditing()
                elif key == 'enter':
                    t = self.edit.edit_text
                    self.stopEditing()
                    self.submitCommand(t)
                else:
                    return key
            else:
                if key == ':' and not self.editing:
                    self.startEditing()
                else:
                    return key

    def submitCommand(self, data):
        arguments = CommandFrame.commandLine.parseString(data).asList()
        function = arguments.pop(0)
        try:
            self.functions[function](*arguments)
        except TypeError:
            # Too many arguments
            tb = traceback.extract_tb(sys.exc_info()[2])
            if len(tb) == 1:
                self.changeStatus("Wrong number of arguments")
            else:
                raise
        except KeyError:
            # Command not found
            tb = traceback.extract_tb(sys.exc_info()[2])
            if len(tb) == 1:
                self.changeStatus("Command not found")
            else:
                raise

    def stopEditing(self):
        self.edit = None
        self.footer = None
        self.focus_position = 'body'
        self.editing = False

    def startEditing(self, startText=''):
        self.edit = urwid.Edit('> ', edit_text=startText, multiline=False)
        self.footer = self.edit
        self.focus_position = "footer"
        self.editing = True

    def changeStatus(self, stat):
        self.footer = urwid.AttrMap(urwid.Text(stat), 'item')


class List(urwid.ListBox):
    def __init__(self, widgets=[], shiftFunc=None):
        body = urwid.SimpleFocusListWalker(widgets)
        self.shiftFunc = shiftFunc
        super(List, self).__init__(body)

    def keypress(self, size, key):
        key = urwid.ListBox.keypress(self, size, key)
        if key == 'j':
            focusWidget, index = self.get_focus()
            if index < len(self.body)-1 and index is not None:
                self.change_focus(size, index+1, coming_from='above')
                if self.shiftFunc:
                    self.shiftFunc(index+1)
        elif key == 'k':
            self.shiftUp()
        else:
            return key

    def shiftDown(self):
        index = self.focus_position
        if index < len(self.body) - 1:
            self.focus_position = index + 1
            if self.shiftFunc is not None:
                self.shiftFunc(index + 1)

    def shiftUp(self):
        index = self.focus_position
        if index > 0:
            self.focus_position = index - 1
            if self.shiftFunc is not None:
                self.shiftFunc(index - 1)


class MappedPile(urwid.Pile):
    filler = urwid.Text("")

    def __init__(self, widgets=[],
                 keymap={}, hitTop=None, hitBottom=None,
                 shiftFunc=None, focus_item=None,
                 space=0, constraint=(lambda x, y: True)):
        widgets = [item
                   for sublist in
                   zip(widgets,
                       *itertools.tee(
                           itertools.repeat(MappedPile.filler),
                           space
                           )
                       )
                   for item in sublist]
        self.constraint = constraint
        self.keymap = keymap
        self.hitTop = hitTop
        self.hitBottom = hitBottom
        self.shiftFunc = shiftFunc
        super(MappedPile, self).__init__(widgets, focus_item)

    def keypress(self, size, key):
        if self.focus.selectable():
            item_rows = self.get_item_rows(size, focus=True) \
                if len(size) == 2 else None
            tsize = self.get_item_size(size, self.focus_position,
                                       True, item_rows)
            key = self.focus.keypress(tsize, key)
        if key == 'j':
            self.shiftDown()
        elif key == 'k':
            self.shiftUp()
        else:
            return key

    def shiftDown(self):
        try:
            nextIndex = (
                index for index, widget in
                enumerate([cont[0] for cont in self.contents])
                if index > self.focus_position
                and widget is not MappedPile.filler
                and self.constraint(index, widget)
                ).next()
            self.focus_position = nextIndex
        except StopIteration:
            if self.hitBottom is not None:
                self.hitBottom()

    def shiftUp(self):
        try:
            nextIndex = (
                index for index, widget in
                reversed(
                    tuple(
                        enumerate([cont[0] for cont in self.contents])
                    )
                )
                if index < self.focus_position
                and widget is not MappedPile.filler
                and self.constraint(index, widget)
                ).next()
            self.focus_position = nextIndex
        except StopIteration:
            if self.hitTop is not None:
                self.hitTop()

    def selectable(self):
        return not self.isEmpty()

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
        elif self.hitTop is not None:
            self.hitTop()

    def isEmpty(self):
        return len(self.contents) == 1

    def add(self, widget):
        self.contents.append((widget, self.options()))
        if len(self.contents) == 2:
            self.focus_position = 1
            print 'yes'

    def set(self, widgets):
        super(TitledPile, self).set((self.title,) + tuple(widgets))
        if len(self.contents) >= 2:
            self.focus_position = 1

    def setTitle(self, widget):
        self.title = widget
        self.contents[0] = (widget, self.options())
