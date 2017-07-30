"""Master process which detects hardware and launches controllers."""

import collections
import json
import multiprocessing
import select
import socket
import time
from pathlib import Path

import pyudev
import setproctitle

from robotd.devices import BOARDS


def _send(connection, message):
    # Split the message into buf_size chunks
    buf_size = BoardRunner.SOCK_BUFFER_SIZE
    for msg in [message[i:i + buf_size] for i in range(0, len(message), buf_size)]:
        connection.send(msg)


class BoardRunner(multiprocessing.Process):
    """Control process for one board."""

    SOCK_BUFFER_SIZE = 2048

    def __init__(self, board, root_dir, **kwargs):
        """Constructor from a given `Board`."""
        super().__init__(**kwargs)

        self.board = board
        self.socket_path = (
            Path(root_dir) / type(board).board_type_id / board.name(board.node)
        )

        self._prepare_socket_path()

        self.connections = []

    def _prepare_socket_path(self):
        try:
            self.socket_path.parent.mkdir(parents=True)
        except FileExistsError:
            if self.socket_path.exists():
                print("Warning: removing old {}".format(self.socket_path))
                self._delete_socket_path()

    def _delete_socket_path(self):
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def _create_server_socket(self):
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)

        server_socket.bind(str(self.socket_path))
        server_socket.listen(5)

        self.socket_path.chmod(0o777)

        setproctitle.setproctitle("robotd {}: {}".format(
            type(self.board).board_type_id,
            type(self.board).name(self.board.node),
        ))

        return server_socket

    def broadcast(self, message):
        message = dict(message)
        message['broadcast'] = True

        msg = (json.dumps(message) + '\n').encode('utf-8')

        for connection in self.connections:
            try:
                _send(connection, msg)
            except ConnectionRefusedError:
                self.connections.remove(connection)

    def _send_board_status(self, connection):
        board_status = self.board.status()
        print('Sending board status:', board_status)
        message = (json.dumps(board_status) + '\n').encode('utf-8')
        _send(new_connection, message)

    def run(self):
        """
        Control this board.

        This is the entry point from the control subprocess and its job is to:

        * Create and manage the UNIX socket in `/var/robotd`,
        * Pass on commands to the `board`,
        * Call `make_safe` whenever the last user disconnects,
        * Deal with error handling and shutdown.
        """

        server_socket = self._create_server_socket()

        self.board.broadcast = self.broadcast
        self.board.start()

        while True:
            # Wait until one of the sockets is ready to read.
            readable, _, errorable = select.select(
                # connections that want to read
                [server_socket] + self.connections,
                # connections that want to write
                [],
                # connections that want to error
                self.connections,
            )

            # New connections
            if server_socket in readable:
                new_connection, _ = server_socket.accept()
                readable.append(new_connection)
                self.connections.append(new_connection)
                print("new connection opened at {}".format(self.socket_path))
                self._send_board_status(new_connection)

            dead_connections = []

            for source in readable:
                if source not in self.connections:
                    continue

                try:
                    blob = source.recv(2048).decode('utf-8').strip()
                except ConnectionResetError:
                    blob = None

                if not blob:
                    print("connection closed")
                    dead_connections.append(source)
                    continue

                try:
                    command = json.loads(blob)
                except ValueError:
                    print("JSON decode fail")
                else:
                    if command != {}:
                        self.board.command(command)
                    self._send_board_status(new_connection)

            dead_connections.extend(errorable)

            self._close_dead_connections(dead_connections)

            if dead_connections and not self.connections:
                print("Last connection closed")
                self.board.make_safe()

    def _close_dead_connections(self, dead_connections):
        for connection in dead_connections:
            connection.close()
            self.connections.remove(connection)

    def cleanup(self):
        """
        Clean up the UNIX socket if it's been left around.

        Called from the parent process.
        """

        self._delete_socket_path()
        self.board.stop()


class MasterProcess(object):
    """The mighty God object which manages the controllers."""

    def __init__(self, root_dir):
        """Standard constructor."""
        self.runners = collections.defaultdict(dict)
        self.context = pyudev.Context()
        self.root_dir = Path(root_dir)

        # Init the startup boards
        for board_type in BOARDS:
            if board_type.create_on_startup:
                self._start_board_instance(board_type, 'startup')

    def tick(self):
        """Poll udev for any new or missing boards."""
        for board_type in BOARDS:
            if hasattr(board_type, 'lookup_keys'):
                nodes = self.context.list_devices(**board_type.lookup_keys)
                self._process_device_list(board_type, nodes)

    def cleanup(self):
        """Shut down all the controllers."""
        for board_type in BOARDS:
            self._process_device_list(board_type, [])

    def _process_device_list(self, board_type, nodes):
        nodes_by_path = {
            x.device_path: x
            for x in nodes
            if board_type.included(x)
        }

        actual_paths = set(nodes_by_path.keys())
        expected_paths = set(self.runners[board_type].keys())

        missing_paths = expected_paths - actual_paths
        new_paths = actual_paths - expected_paths

        for new_device in new_paths:
            print(
                "Detected new %s: %s (%s)" % (
                    board_type.__name__,
                    new_device,
                    board_type.name(nodes_by_path[new_device]),
                ),
            )
            self._start_board_instance(board_type, new_device, node=nodes_by_path[new_device])

        for dead_device in missing_paths:
            print("Disconnected %s: %s" % (board_type.__name__, dead_device))
            runner = self.runners[board_type][dead_device]
            runner.terminate()
            runner.join()
            runner.cleanup()
            del self.runners[board_type][dead_device]

    def _start_board_instance(self, board_type, new_device, **kwargs):
        instance = board_type(**kwargs)
        runner = BoardRunner(instance, self.root_dir)
        runner.start()
        self.runners[board_type][new_device] = runner


def main(**kwargs):
    """Main entry point."""
    master = MasterProcess(**kwargs)

    setproctitle.setproctitle("robotd master")

    try:
        while True:
            master.tick()
            time.sleep(1)

    except KeyboardInterrupt:
        master.cleanup()


def main_cmdline():
    # Parse terminal arguments
    import argparse
    parser = argparse.ArgumentParser()

    default_root_dir = Path("/var/robotd")
    parser.add_argument(
        "--root-dir",
        type=Path,
        help="directory to run root of robotd at (defaults to {})".format(
            default_root_dir,
        ),
        default=default_root_dir,
    )
    args = parser.parse_args()

    main(
        root_dir=args.root_dir,
    )


if __name__ == '__main__':
    main_cmdline()
