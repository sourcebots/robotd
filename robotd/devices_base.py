import re


class BoardMeta(type):
    BOARDS = []

    def __new__(cls, name, bases, dict):
        cls = type.__new__(cls, name, bases, dict)
        if hasattr(cls, 'lookup_keys') and cls.enabled:
            BoardMeta.BOARDS.append(cls)
        return cls

    @property
    def board_type_id(self):
        full_name = self.__name__

        if full_name.endswith('Board'):
            full_name = full_name[:-5]

        return re.sub(
            r'(?!\A)[A-Z]',
            r'_\g<0>',
            full_name,
        ).lower()


class Board(metaclass=BoardMeta):
    enabled = True

    @classmethod
    def name(cls, node):
        return node.sys_name

    def __init__(self, node):
        self.node = node

    def start(self):
        pass

    def make_safe(self):
        pass

    def status(self):
        return {}

    def command(self, cmd):
        pass
