from typing import ClassVar


class Model:
    def dict(self):
        return "synthetic-module-model"


patch = Model()


class C:
    from unittest.mock import patch

    values: ClassVar[list[str]] = [patch.dict() for item in [0]]
