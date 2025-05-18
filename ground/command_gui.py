import ctypes
import queue
import socket
import sys
import threading

import PyQt6.QtWidgets as wid
from PyQt6.QtCore import Qt
from PyQt6 import QtCore
from PyQt6 import QtGui

import ground_ports
import support
from impisc.network import comm
from impisc.network import ports as remote_ports
from impisc.network import packets

remote_address = (remote_ports.GRIPS_IP, remote_ports.COMMAND_ROUTER)


class CommanderWindow(wid.QMainWindow):
    def __init__(self, commander: comm.Commander):
        super().__init__(parent=None)
        self.commander = commander

        self.setWindowTitle("IMPISH commander")
        self.main_widget = wid.QWidget(parent=self)
        self.setCentralWidget(self.main_widget)

        # Allow quit with ctrl+q
        combo = QtGui.QKeySequence("Ctrl+Q")
        self.shortcut = QtGui.QShortcut(combo, self)
        self.shortcut.activated.connect(self.close)

        # Forward-declare variables for access later
        self.ack_box: wid.QPlainTextEdit
        self.out_box: wid.QPlainTextEdit
        self.cmd_box: wid.QLineEdit
        self.go_button: wid.QPushButton
        self._make_layout()

        self.go_button.clicked.connect(self.send_command)

    def _make_layout(self):
        """Create all the main-window widgets and place them"""
        layout = wid.QGridLayout()
        # Constrain the size so labels don't grow weirdly
        layout.setSizeConstraint(layout.SizeConstraint.SetMinimumSize)
        layout.addWidget(
            wid.QLabel("<h2>output</h2>"), 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(
            wid.QLabel("<h2>acks</h2>"), 0, 2, 1, 2, Qt.AlignmentFlag.AlignCenter
        )

        # Displays command output (retcode, stdout, stderr)
        self.out_box = wid.QPlainTextEdit()
        layout.addWidget(self.out_box, 1, 0, 3, 2)

        # Displays command acknowledgements
        self.ack_box = wid.QPlainTextEdit()
        layout.addWidget(self.ack_box, 1, 2, 3, 2)

        # Common configuration between the displays
        for box in (self.out_box, self.ack_box):
            box.setReadOnly(True)
            box.setLineWrapMode(self.out_box.LineWrapMode.NoWrap)

        # Users input commands into this
        self.cmd_box = wid.QLineEdit()
        self.cmd_box.setPlaceholderText("Enter a command")
        layout.addWidget(self.cmd_box, 4, 0, 1, 3)

        # Users push this button to send the command off
        self.go_button = wid.QPushButton("send cmd")
        layout.addWidget(self.go_button, 4, 3)

        # Tell the layout which rows should grow upon resize
        last_row = 4
        for row in range(5):
            layout.setRowStretch(row, int(row != 0 and row != last_row))

        self.main_widget.setLayout(layout)

    def send_command(self):
        """Get the command from the text box and send it to the remote system."""
        cmd = self.cmd_box.text()
        if len(cmd) > ctypes.sizeof(packets.CommandCharArray):
            msg = wid.QMessageBox(parent=self)
            msg.setText(
                f"Command too long. Limit is 255 characters. You have {len(cmd)}"
            )
            msg.setIcon(msg.Icon.Warning)
            msg.setStandardButtons(msg.StandardButton.Ok)
            _ = msg.exec()
            return
        self.cmd_box.setText("")

        packet = packets.ArbitraryLinuxCommand()
        packet.command[: len(cmd)] = cmd.encode("utf-8")
        self.commander.send_command(packet, remote_address)

        msg = wid.QMessageBox(parent=self)
        msg.setText(f'Sent command: "{cmd}"')
        msg.setIcon(msg.Icon.Information)
        msg.setStandardButtons(msg.StandardButton.Ok)
        _ = msg.exec()


class TimedDequeuer:
    """Dequeue objects and push them onto a QPlainTextEdit widget."""

    def __init__(
        self, cadence_ms: int, data_queue: queue.Queue, box: wid.QPlainTextEdit
    ):
        self.cadence = cadence_ms
        self.queue = data_queue
        self.box = box

        self.timer = QtCore.QTimer(parent=box)
        self.timer.timeout.connect(self.update_box)
        self.timer.start(self.cadence)

    def update_box(self):
        """Get data off of the queue and put it into the box"""
        while self.queue.qsize() != 0:
            parsed = self.queue.get_nowait()
            cursor = self.box.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.box.insertPlainText(repr(parsed) + "\n")

            # Keep the view scrolled to the bottom
            scrollbar = self.box.verticalScrollBar()
            if scrollbar is not None:
                scrollbar.setValue(scrollbar.maximum())
        self.timer.start(self.cadence)


def init_threads_queues():
    # Set up machinery for command acks
    ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ack_sock.bind(("", ground_ports.COMMAND_ACK_DISPLAY))
    ack_queue = support.CommandAckQueue(data_stream=ack_sock, history_length=5)

    # Set up machinery for receiving telemetry back
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind(("", ground_ports.COMMAND_TELEMETRY))
    listen_timeout = 1
    telem_queue = support.LinuxCommandResponseParser(
        listen_socket=cmd_sock, assumed_done_timeout=listen_timeout
    )

    def await_acks():
        while True:
            ack_queue.accept_new()

    def await_telem():
        while True:
            telem_queue.accept_and_enqueue()

    ack_thread = threading.Thread(target=await_acks)
    telem_thread = threading.Thread(target=await_telem)

    # The threads are data-delivering daemons: don't block app exit
    ack_thread.daemon = True
    telem_thread.daemon = True

    ack_thread.start()
    telem_thread.start()
    return (ack_queue, telem_queue)


if __name__ == "__main__":
    ack_queue, telem_queue = init_threads_queues()

    app = wid.QApplication([])
    cmd = comm.Commander(ground_ports.COMMANDER)
    window = CommanderWindow(commander=cmd)
    with open("commander.qss", "r") as f:
        style = f.read()
    window.setStyleSheet(style)
    window.show()

    # Add the control to connect the model with the GUI
    update_cadence_ms = 100
    ack_ctrl = TimedDequeuer(update_cadence_ms, ack_queue.queue, window.ack_box)
    cmd_ctrl = TimedDequeuer(update_cadence_ms, telem_queue.ready_queue, window.out_box)

    sys.exit(app.exec())
