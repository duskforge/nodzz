"""Simple utils and boilerplate code."""

import json
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from nodzz.basic_types import JSONType


def load_yaml(file_path: Path) -> JSONType:
    """Reads YAML file contents into python object.

    Args:
         file_path: Yaml file path in pathlib format.

    Returns:
         Yaml file contents loaded into python object.
    """
    with file_path.open('r', encoding='utf8') as f:
        result = yaml.safe_load(f)

    return result


def load_json(file_path: Path) -> JSONType:
    """Reads JSON file contents into python object.

        Args:
             file_path: Json file path in pathlib format.

        Returns:
             Json file contents loaded into python object.
        """
    with file_path.open('r', encoding='utf8') as f:
        result = json.load(f)

    return result


def load_file(file_path: Path) -> JSONType:
    """Reads JSON and YAML contents files into Python object.

    Method wraps JSON and YAML files load.

    Args:
        file_path: ``pathlib`` object with configuration file path.

    Returns:
        Object with loaded file contents.
    """
    if file_path.suffix == '.json':
        return load_json(file_path)
    elif file_path.suffix in ['.yaml', '.yml']:
        return load_yaml(file_path)
    else:
        raise ValueError(f'Unsupported extension of file: {str(file_path)}, can handle only .yaml, .yml or .json')


def import_by_name(name: str) -> Any:
    """Imports Python object using its full path in str format.

    Args:
        name: Object full string path, compiled of dot-delimited modules names
            and object name.

    Returns:
        Imported object.
    """
    module_name = name.rsplit('.', 1)
    object_name = module_name.pop(-1)
    module_name = module_name[0] if module_name else '__init__'
    return getattr(import_module(module_name), object_name)
