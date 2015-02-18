import urwid
import sys
import traceback
import pyparsing as pp


class CommandFrame(urwid.Frame):
    argument = pp.Or((pp.Word(pp.printables), pp.QuotedString("'")))
    command = pp.Word(pp.alphas)
    commandLine = command + pp.ZeroOrMore(argument)

    def __init__(self, body=None, header=None, focus_part='body'):
        self.editing = False
        self.edit = None
        self.functions = {}
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
            #Too many arguments
            tb = traceback.extract_tb(sys.exc_info()[2])
            if len(tb) == 1:
                self.changeStatus("Wrong number of arguments")
            else:
                raise
        except KeyError:
            #Command not found
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
            focusWidget, index = self.get_focus()
            if index > 0 and index is not None:
                self.change_focus(size, index-1, coming_from='below')
                if self.shiftFunc:
                    self.shiftFunc(index-1)
        else:
            return key

