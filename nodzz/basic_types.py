"""Complex type annotations and basic data structures used throughout the project."""

from __future__ import annotations

from enum import Enum
from typing import Union, List, Dict


# JSON-serializable data types annotations.
JSONSimpleType = Union[int, float, bool, None, str]
JSONType = Union[JSONSimpleType, List['JSONType'], Dict[str, 'JSONType']]
JSONList = List[JSONType]
JSONDict = Dict[str, JSONType]
JSON = Union[JSONList, JSONDict]


class NodeStatus(Enum):
    READY = 0
    RUNNING = 1
    SUCCESS = 2
    FAILED = 3
