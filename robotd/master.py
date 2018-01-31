"""Master process which detects hardware and launches controllers."""

import collections
import json
import multiprocessing
import select
import shutil
import socket
import threading
import time
from pathlib import Path

import pyudev
import setproctitle

from .devices import BOARDS


class Connection:
    """
    A connection to a device.

    This wraps a ``socket.socket`` providing encoding and decoding so that
    consumers of this class can send and receive JSON-compatible typed data
    rather than needing to worry about lower-level details.
    """

    def __init__(self, socket):
        """Wrap the given socket."""
        self.socket = socket
        self.data = b''

    def close(self):
        """Close the connection."""
        self.socket.close()

    def send(self, message):
        """Send the given JSON-compatible message over the connection."""
        line = json.dumps(message).encode('utf-8') + b'\n'
        self.socket.sendall(line)

    def receive(self):
        """Receive a single message from the connection."""
        while b'\n' not in self.data:
            message = self.socket.recv(4096)
            if message == b'':
                return None

            self.data += message
        line = self.data.split(b'\n', 1)[0]
        self.data = self.data[len(line) + 1:]

        return json.loads(line.decode('utf-8'))


class BoardRunner(multiprocessing.Process):
    """Control process for one board."""

    def __init__(self, board, root_dir, **kwargs):
        super().__init__(**kwargs)

        self.board = board
        self.socket_path = (
            Path(root_dir) / type(board).board_type_id / board.name(board.node)
        )

        self._prepare_socket_path()

        self.connections = {}

    def _prepare_socket_path(self):
        try:
            self.socket_path.parent.mkdir(parents=True)
        except FileExistsError:
            if self.socket_path.exists():
                print('Warning: removing old {}'.format(self.socket_path))
                self._delete_socket_path()

    def _delete_socket_path(self):
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def _create_server_socket(self):
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        server_socket.bind(str(self.socket_path))
        server_socket.listen(5)

        self.socket_path.chmod(0o777)

        print('Listening on:', self.socket_path)

        setproctitle.setproctitle('robotd {}: {}'.format(
            type(self.board).board_type_id,
            type(self.board).name(self.board.node),
        ))

        return server_socket

    def broadcast(self, message):
        """Broadcast a message over all connections."""
        message = dict(message)
        message['broadcast'] = True

        for connection in self.connections.values():
            try:
                connection.send(message)
            except ConnectionRefusedError:
                self.connections.remove(connection)

    def _send_board_status(self, connection):
        board_status = self.board.status()
        print('Sending board status:', board_status)
        connection.send(board_status)

    def _send_command_response(self, connection, response):
        message = {'response': response}
        print('Sending command response:', message)
        connection.send(message)

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
            connection_sockets = list(self.connections.keys())

            # Wait until one of the sockets is ready to read.
            readable, _, errorable = select.select(
                # connections that want to read
                [server_socket] + connection_sockets,
                # connections that want to write
                [],
                # connections that want to error
                connection_sockets,
            )

            # New connections
            if server_socket in readable:
                new_socket, _ = server_socket.accept()
                new_connection = Connection(new_socket)
                readable.append(new_socket)
                self.connections[new_socket] = new_connection
                print('New connection at:', self.socket_path)
                self._send_board_status(new_connection)

            dead_sockets = []

            for sock in readable:
                try:
                    connection = self.connections[sock]
                except KeyError:
                    continue

                command = connection.receive()

                if command is None:
                    dead_sockets.append(sock)
                    continue

                if command != {}:
                    response = self.board.command(command)
                    if response is not None:
                        self._send_command_response(connection, response)

                self._send_board_status(connection)

            dead_sockets.extend(errorable)

            self._close_dead_sockets(dead_sockets)

            if dead_sockets and not self.connections:
                print('Last connection closed')
                self.board.make_safe()

    def _close_dead_sockets(self, dead_sockets):
        for sock in dead_sockets:
            try:
                del self.connections[sock]
            except KeyError:
                pass
            sock.close()

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
        self.runners = collections.defaultdict(dict)
        self.context = pyudev.Context()
        self.root_dir = Path(root_dir)

        self.root_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        self.clear_socket_files()

        self.runners_lock = threading.Lock()

        # Init the startup boards
        for board_type in BOARDS:
            if board_type.create_on_startup:
                self._start_board_instance(board_type, 'startup')

    def clear_socket_files(self):
        for path in self.root_dir.iterdir():
            shutil.rmtree(str(path))

    def tick(self):
        """Poll udev for any new or missing boards."""
        for board_type in BOARDS:
            if hasattr(board_type, 'lookup_keys'):
                nodes = self.context.list_devices(**board_type.lookup_keys)
                initialized_nodes = [n for n in nodes if n.is_initialized]
                self._process_device_list(board_type, initialized_nodes)

    def cleanup(self):
        """Shut down all the controllers."""
        for board_type in BOARDS:
            self._process_device_list(board_type, [])
        self.stop_monitor()

    def _process_device_list(self, board_type, nodes):
        with self.runners_lock:
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
                    'Detected new %s: %s (%s)' % (
                        board_type.__name__,
                        new_device,
                        board_type.name(nodes_by_path[new_device]),
                    ),
                )
                self._start_board_instance(
                    board_type,
                    new_device,
                    node=nodes_by_path[new_device],
                )

            for dead_device in missing_paths:
                print('Disconnected %s: %s' % (
                    board_type.__name__,
                    dead_device,
                ))
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

    def launch_monitor(self):
        self.monitor_stop_flag = False
        self.monitor_thread = threading.Thread(target=self._monitor_thread)
        self.monitor_thread.start()

    def stop_monitor(self):
        self.monitor_stop_flag = True
        self.monitor_thread.join()

    def _monitor_thread(self):
        while True:
            if self.monitor_stop_flag:
                return

            time.sleep(0.5)

            with self.runners_lock:
                for board_type, runners in list(self.runners.items()):
                    for device_id, runner_process in list(runners.items()):
                        if not runner_process.is_alive():
                            print('Dead worker: {}({})'.format(
                                board_type,
                                device_id,
                            ))
                            # This worker has died and needs to be reaped
                            del self.runners[board_type][device_id]


def main(**kwargs):
    """Main entry point."""
    master = MasterProcess(**kwargs)

    setproctitle.setproctitle('robotd master')

    master.launch_monitor()
    try:
        while True:
            master.tick()
            time.sleep(1)
    except KeyboardInterrupt:
        master.cleanup()


def main_cmdline():
    """Command line entry point."""
    import argparse
    parser = argparse.ArgumentParser()

    default_root_dir = Path('/var/robotd')
    parser.add_argument(
        '--root-dir',
        type=Path,
        help='directory to run root of robotd at (defaults to {})'.format(
            default_root_dir,
        ),
        default=default_root_dir,
    )
    args = parser.parse_args()

    main(root_dir=args.root_dir)


if __name__ == '__main__':
    main_cmdline()
