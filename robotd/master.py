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


class BoardRunner(multiprocessing.Process):
    """Control process for one board."""

    def __init__(self, board, **kwargs):
        """Constructor from a given `Board`."""
        super().__init__(**kwargs)
        self.board = board
        self.socket_path = Path("/var/robotd/{}/{}".format(
            type(board).board_type_id,
            board.name(board.node),
        ))
        try:
            self.socket_path.parent.mkdir(parents=True)
        except FileExistsError:
            if self.socket_path.exists():
                print("Warning: removing old {}".format(self.socket_path))
                self.socket_path.unlink()
        print(self.socket_path)

    def run(self):
        """
        Control this board.

        This is the entry point from the control subprocess and its job is to:

        * Create and manage the UNIX socket in `/var/robotd`,
        * Pass on commands to the `board`,
        * Call `make_safe` whenever the last user disconnects,
        * Deal with error handling and shutdown.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        sock.bind(str(self.socket_path))
        sock.listen(5)

        self.socket_path.chmod(0o777)

        setproctitle.setproctitle("robotd {}: {}".format(
            type(self.board).board_type_id,
            type(self.board).name(self.board.node),
        ))

        connections = []

        def broadcast(message):
            nonlocal connections

            message = dict(message)
            message['broadcast'] = True

            msg = (json.dumps(message) + '\n').encode('utf-8')

            retained_connections = []

            for connection in list(connections):
                try:
                    connection.send(msg)
                except ConnectionRefusedError:
                    pass
                else:
                    retained_connections.append(connection)

            connections = retained_connections

        self.board.broadcast = broadcast
        self.board.start()

        while True:
            (readable, _, errorable) = select.select(
                [sock] + connections,
                [],
                connections,
            )

            # New connections
            if sock in readable:
                (new_connection, _) = sock.accept()
                readable.append(new_connection)
                connections.append(new_connection)
                print("new connection opened")

                new_connection.send((
                    json.dumps(self.board.status()) + '\n'
                ).encode('utf-8'))

            dead_connections = []

            for source in readable:
                if source not in connections:
                    continue

                blob = source.recv(2048).decode('utf-8').strip()

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
                    source.send((
                        json.dumps(self.board.status()) + '\n'
                    ).encode('utf-8'))

            for source in errorable:
                print("err? ", source)
                dead_connections.append(source)

            for dead_connection in dead_connections:
                dead_connection.close()
                connections.remove(dead_connection)

            if dead_connections and not connections:
                print("Last connection closed")
                self.board.make_safe()

    def cleanup_socket(self):
        """
        Clean up the UNIX socket if it's been left around.

        Called from the parent process.
        """
        try:
            self.socket_path.unlink()
        except FileNotFoundError:
            pass


class MasterProcess(object):
    """The mighty God object which manages the controllers."""

    def __init__(self):
        """Standard constructor."""
        self.runners = collections.defaultdict(dict)
        self.context = pyudev.Context()

    def tick(self):
        """Poll udev for any new or missing boards."""
        for board_type in BOARDS:
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
            instance = board_type(nodes_by_path[new_device])
            runner = BoardRunner(instance)
            runner.start()
            self.runners[board_type][new_device] = runner

        for dead_device in missing_paths:
            print("Disconnected %s: %s" % (board_type.__name__, dead_device))
            runner = self.runners[board_type][dead_device]
            runner.terminate()
            runner.join()
            runner.cleanup_socket()
            del self.runners[board_type][dead_device]


def main():
    """Main entry point."""
    master = MasterProcess()

    setproctitle.setproctitle("robotd master")

    try:
        while True:
            master.tick()
            time.sleep(1)

    except KeyboardInterrupt:
        master.cleanup()


if __name__ == '__main__':
    main()
