import pytest
from mock import Mock, create_autospec
from urwidgets import CommandFrameController

class TestCommandFrameController:
    def setup_method(self):
        self.widget = Mock()
        self.widget.escape = Mock(lambda x: None)
        self.widget.change_status = Mock()
        self.widget.stop_editing = Mock()

        self.commands = {
            'command' : Mock() 
        }
        self.sut = CommandFrameController(self.widget, self.commands)

    def test_areyousure_yes(self):
        yes = Mock()
        no = Mock()

        yes_func, no_func = self.sut.areyousure(yes, no)
        yes_func()

        yes.assert_called_once()
        self.widget.escape.assert_called_once()
        no.assert_not_called()


    def test_areyousure_no(self):
        yes = Mock()
        no = Mock()

        yes_func, no_func = self.sut.areyousure(yes, no)
        no_func()

        no.assert_called_once()
        self.widget.escape.assert_called_once()
        yes.assert_not_called()

    def test_submit_command_invalid_command(self):
        command = 'This is a "test'
        
        self.sut.submit_command(command)

        self.widget.change_status.assert_called_once_with("Invalid command")
        self.commands['command'].assert_not_called()

    def test_submit_command_not_found(self):
        command = 'c'

        self.sut.submit_command(command)

        self.widget.change_status.assert_called_once_with("Command not found")
        self.commands['command'].assert_not_called()

    def test_submit_command_wrong_arguments(self):
        commands = {
            'command' : create_autospec(lambda: None)
        }
        sut = CommandFrameController(self.widget, commands)
        command = 'command testing testing'

        sut.submit_command(command)

        self.widget.change_status.assert_called_once_with("Wrong number of arguments")

    def test_submit_command(self):
        command = 'command'

        self.sut.submit_command(command)
        
        self.commands['command'].assert_called_once()

    def test_submit_command_multiple_arguments(self):
        command = 'command testing testing'

        self.sut.submit_command(command)

        self.commands['command'].assert_called_once_with('testing', 'testing')

    def test_submit_command_quoted(self):
        command = 'command "testing testing" another'

        self.sut.submit_command(command)

        self.commands['command'].assert_called_once_with('testing testing', 'another')

    def test_start_editing_complete(self):
        self.widget.command_line_text = 'yes'
        
        complete, enter, backspace = self.sut.start_editing(None, ('yesterday',))
        complete()

        assert self.widget.command_line_text == 'yesterday'
        assert self.widget.command_line_position == len('yesterday')

    def test_start_editing_enter_no_callback(self):
        self.sut.submit_command = Mock()
        self.widget.command_line_text = 'command'
        
        complete, enter, backspace = self.sut.start_editing(None, [])
        enter()

        self.widget.stop_editing.assert_called_once()
        self.sut.submit_command.assert_called_once_with('command')

    def test_start_editing_enter_with_callback(self):
        self.sut.submit_command = Mock()
        self.widget.command_line_text = 'new command'
        callback = Mock()

        complete, enter, backspace = self.sut.start_editing(callback, ())
        enter()

        self.widget.stop_editing.assert_called_once()
        self.sut.submit_command.assert_not_called()
        callback.assert_called_once_with('new command')

    def test_start_editing_backspace_empty_text(self):
        self.sut.submit_command = Mock()
        self.widget.command_line_text = ''
        callback = Mock()

        complete, enter, backspace = self.sut.start_editing(callback, ())
        backspace()

        self.widget.stop_editing.assert_called_once()
        self.sut.submit_command.assert_not_called()
        callback.assert_not_called()

    def test_start_editing_backspace_empty_text(self):
        self.sut.submit_command = Mock()
        self.widget.command_line_text = 'not empty command'
        callback = Mock()

        complete, enter, backspace = self.sut.start_editing(callback, ())
        backspace()

        self.widget.stop_editing.assert_not_called()
        self.sut.submit_command.assert_not_called()
        callback.assert_not_called()

