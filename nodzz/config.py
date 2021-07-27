"""Configuration management tools.

While ``nodzz`` have the instruments to implement, manage and configure any
behavior tree via pure Python API, this is of course not the most convenient
way to manage behavior trees based projects. ``nodzz`` provides config based
behavior tree management tools which allow completely separate tree graph
design and nodes configuring from each particular node Python implementation.
Here are the core concepts of ``nodzz`` configuration:

Component.

Component is a ``nodzz`` project atomic building block (like node
or some connector, for example).

In the ``nodzz`` configuration tools component is represented by unique name
which identifies it among all other components and its config. From here on,
the ter "component name" and the term "config name" will mean the same.
Component config is a JSON-serializable mapping data structure which can
exist both in the form of ``JSONDict`` (JSON-serializable dict) and in the
form of ``pydantic`` based ``ConfigModelBase`` config which in turn can be
one-to-one converted from or to the ``JSONDict`` representation. Please refer
``ConfigModelBase`` class documentation for more info.

Each component config must have one (and only one) of two fields initialised:
``class_name`` or ``component_name``.
* ``class_name`` is a full import path to the python class which implements
the component and which is initialized with the config. Import path should
should locate component class in current Python environment and has format
like ``nodzz.nodes.controllers.SequenceNode``. If ``class_name`` is initialised,
component config should provide all necessary parameters for the component
correct work.
* ``component_name`` is a reference to the name of some other ``nodzz`` component
(referenced component) in the configuration namespace. In this case referenced
config will be merged to the initial config: all uninitialized fields in the
initial component config will be automatically filled by corresponding values
from the referenced component config. This process is called "config resolution".
Also the component being referenced can itself have a reference to another
component. In such case config resolution process covers all configs chain.
This feature implements some kind of inheritance among the components configs
and encourages components reuse.

Config set.

Config set as a logical entity is a set (surprise!) of component configs that
exist in the same namespace. This allows to identify and access all component
configs by their names. Config set implemented in the config set entity.

"""
# TODO: Some of the docstrings parts should be moved to docs.
# TODO: Implement config dirs loading.

from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from nodzz.basic_types import JSONDict
from nodzz.utils import load_file


class ConfigSet:
    """Component configs management entity.

    ``ConfigSet`` is a container for component configs, loaded from external sources
    like files or databases. It provides instruments for configs access, management
    and validation. ``ConfigSet`` serves as a library of component configs. All configs
    required for any behavior initialisation tree should be contained in one instance
    of ``ConfigSet``.
    """
    def __init__(self) -> None:
        self._meta_configs = {}

    def add_config(self, name: str, config: JSONDict, source: str = 'undefined', update: bool = False) -> None:
        """Adds component config to the config set.

        Adds component config and its metadata to the config set, validates and
        optionally resolves config.

        Args:
            name: Config name.
            config: Component config in JSON-serializable dict format.
            source: Config source ID, used for config source identification in case
                of config management problems.
            update: Boolean flag controlling the behavior when config with already
                existing name is being added. If value is ``True``, existing config will
                be replaced by the new one. If value is ``False``, exception will be raised.
                Default value is ``False``.
        """
        class_name = config.get('class_name')
        ref_name = config.get('component_name')

        if class_name and ref_name:
            raise ValueError(f'Both class_name and component_name are defined in config: {name}(source: {source})')
        elif not class_name and not ref_name:
            raise ValueError(f'Both class_name and component_name are not defined in config: {name} (source: {source})')

        if name in self._meta_configs and not update:
            raise ValueError(f'Trying to add config with already existing name: {name}, '
                             f'new config source: {source}, '
                             f'existing config source: {self._meta_configs[name]["source"]}')

        # TODO: Now is assigning used only for debug mode. Remove when name/module configuration will be implemented.
        config['name'] = name

        self._meta_configs[name] = {
            'config': config,
            'source': source
        }

    def get_config(self, name: str) -> Optional[JSONDict]:
        """Returns config from the config set by its name.

        Args:
            name: Config name.

        Returns:
            JSONDict component config if config with given name exists in
            config set, else ``None``.
        """
        meta_config = self._meta_configs.get(name)
        result = meta_config['config'] if meta_config else None
        return result

    def del_config(self, name: str) -> None:
        """Deletes config from the config set by its name.

        Args:
            name: Config name.
        """
        self._meta_configs.pop(name, None)

    def _resolve_config(self, name: str, config: JSONDict, source: str, chain: Optional[List[str]] = None) -> JSONDict:
        """Resolves component config.

        Recursively resolves all configs in reference chain of given config (including
        given config itself). References are looked among already loaded to the config
        set configs.

        Args:
            name: Config name.
            config: Component config in JSON-serializable dict format.
            source Config source ID, used for config source identification in case
                of config management problems.
            chain: List which accumulates non-resolved config names in the method
                recursive calls cycle. Used for the cyclic references detection in
                the component configs.

        Returns:
            Dict containing all resolved configs from the reference chain of given
            config. Keys are config names and values are corresponding configs. Empty
            dict is returned when no config was resolved.
        """
        result = {}
        ref_name = config.get('component_name')

        if ref_name:
            ref_meta_config = self._meta_configs.get(ref_name)

            if ref_meta_config is None:
                raise ValueError(f'Component {name} (source: {source}) refers to the absent component {ref_name}')

            chain = chain or []

            if ref_name in chain:
                error_message = 'Cyclic reference among component configs: '

                for _name in chain:
                    _ref_name = self._meta_configs[_name]['config']['component_name']
                    _source = self._meta_configs[_name]['source']
                    info_str = f'\n\tname: {_name}, refers to: {_ref_name}, source: {_source}'
                    info_str = f'\n{info_str}' if _name == ref_name else info_str
                    error_message = f'{error_message}{info_str}'

                info_str = f'\n\tname: {name}, refers to: {ref_name}, source: {source}'
                error_message = f'{error_message}{info_str}'

                raise ValueError(f'Cyclic reference among components:\n{error_message}')

            ref_config = ref_meta_config['config']
            ref_ref_name = ref_config.get('component_name')

            if ref_ref_name:
                chain.append(name)
                ref_source = ref_meta_config['source']
                result = self._resolve_config(ref_name, ref_config, ref_source, chain)
                ref_config = result[ref_name]

            resolved_config = {k: v for k, v in ref_config.items()}
            resolved_config.update(**config)
            resolved_config.pop('component_name')

            result[name] = resolved_config

        return result

    def resolve_configs(self) -> None:
        """Prepares all config set configs for components initialisation.

        "Flattens" config set structure: resolves all references between
        configs by setting field values which are absent in config with
        corresponding field values from referenced config.
        """
        for name, meta_config in self._meta_configs.items():
            config = meta_config['config']
            source = meta_config['source']
            resolved_configs = self._resolve_config(name=name, config=config, source=source)

            for config_name, resolved_config in resolved_configs.items():
                self._meta_configs[config_name]['config'] = resolved_config


class _ConfigFileModel(BaseModel):
    """Config file validation model."""
    __root__: Dict[str, Dict[str, Any]]


def load_config_file(file_path: Path) -> ConfigSet:
    """Loads component configs from single JSON/YAML file and initialises ``ConfigSet`` entity.

    File should contain dict as a root element where keys are config names and
    values are configs.

    Args:
        file_path: ``pathlib`` object with configuration file path.

    Returns:
        ``ConfigSet`` instance with resolved configs loaded from file.
    """
    config_dict = load_file(file_path)
    _ConfigFileModel.parse_obj(config_dict)
    config_set = ConfigSet()
    file_path_str = str(file_path)

    for name, config in config_dict.items():
        config_set.add_config(name=name, config=config, source=file_path_str)

    config_set.resolve_configs()

    return config_set
