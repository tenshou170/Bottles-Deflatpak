# sh.py

import re

_is_name = re.compile(r"""[_a-zA-Z][_a-zA-Z0-9]*""")


class ShUtils:
    @staticmethod
    def is_name(text: str) -> bool:
        return bool(_is_name.fullmatch(text))

    @staticmethod
    def split_assignment(text: str) -> tuple[str, str]:
        name, _, value = text.partition("=")
        return (name, value)
