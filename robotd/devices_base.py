"""Base classes for boards and peripherals."""

import re


class BoardMeta(type):
    """
    Metaclass for `Board` subclasses.

    This is here to automatically add the instances to a registry.
    """

    BOARDS = []

    def __new__(cls, name, bases, dict):
        """Instantiate subclass."""
        cls = type.__new__(cls, name, bases, dict)
        if (
            (hasattr(cls, 'lookup_keys') or cls.create_on_startup) and
            cls.enabled
        ):
            BoardMeta.BOARDS.append(cls)
        return cls

    @property
    def board_type_id(self):
        """
        Human readable description of the board type.

        Provided in snake case. Defaults to some magic to try to infer this
        from the name of the class, but can be overridden by assigning a
        string to `board_type_id` in a subclass.
        """
        if 'board_type_id' in self.__dict__:
            return self.__dict__['board_type_id']

        full_name = self.__name__

        if full_name.endswith('Board'):
            full_name = full_name[:-5]

        return re.sub(
            r'(?!\A)[A-Z]',
            r'_\g<0>',
            full_name,
        ).lower()


class Board(metaclass=BoardMeta):
    """
    Parent class for types of board and peripheral.

    Subclasses define how to detect these boards, and how to actually
    interact with them.
    """

    enabled = True
    create_on_startup = False

    @classmethod
    def name(cls, node):
        """Simple node name."""
        return node.sys_name

    @classmethod
    def included(cls, node):
        """Mechanism for excluding nodes."""
        return True

    def __init__(self, node):
        """Standard constructor, run in the master process."""
        self.node = node

    def start(self):
        """Open connection to peripheral."""
        pass

    def make_safe(self):
        """
        Set peripheral to a safe state.

        This is called after control connections have died.
        """
        pass

    def stop(self):
        """Close connection to the peripheral."""
        pass

    def status(self):
        """Brief status description of the peripheral."""
        return {}

    def command(self, cmd):
        """Run user-provided command."""
        pass
