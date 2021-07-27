"""Core entities: base classes and full implementations."""
# TODO: Some of the docstrings parts should be moved to docs.
# TODO: Add logging.
# TODO: Fix snippet formatting in docstrings.

from typing import TypeVar, Dict, Optional, Union

from pydantic import BaseSettings

from nodzz.basic_types import JSONType, JSONDict, NodeStatus


# TODO: Implement module/name fields based configuration.
# TODO: Implement caption field.
class ConfigModelBase(BaseSettings):
    """Base model for component configs.

    Any ``nodzz`` component config can be JSON serializable dict (``JSONDict``) or
    ``pydantic`` BaseSettings model. If second, config model should be derived
    from this class. Fields defined on the ``nodzz`` library level should not be
    overridden or used for the logic they were not designed for.

    ``JSONDict`` representation allows to manage ``nodzz`` configuration via JSON
    and YAML files, database or even graphic tools.

    ``ConfigModelBase`` based component config models offer such features as default
    values definition, better autodocumentation and autocompletion in IDE as
    well as ``pydantic`` features like validation and autofilling parameters
    values from environment variables. Component config model can be defined
    by assigning config model class as a value to the ``config_model`` component
    class-level variable. We are strongly encouraging you to define config model
    for each component you create in your ``nodzz`` powered projects.

    Attributes:
        name: Str with component name.
        class_name: Str with full import path to the python class which implements
            component. Field is used only when parsing ``JSONDict`` config. Mutually
            exclusive with ``component_name`` attribute.
        component_name: is a reference to the name of some other ``nodzz`` component
            in the configuration namespace. Field is used only when parsing ``JSONDict``
            config.  Mutually exclusive with ``class_name`` attribute.
    """
    name: Optional[str] = None
    class_name: Optional[str] = None
    component_name: Optional[str] = None


TConfigModel = TypeVar('TConfigModel', bound=ConfigModelBase)
TConfig = Union[JSONDict, TConfigModel]


class ComponentBase:
    """Base class for any ``nodzz`` project component.

    Component is a ``nodzz`` project atomic building block (like node or some connector,
    for example). Any ``nodzz`` component should derive from this class. If component is
    configurable, its config can be defined through the class derived from ``ConfigModelBase``
    (which is ``pydantic`` config models in fact or JSON serializable dict (``JSONDict``)
    config can be used.

    Attributes:
        config_model: Component config class derived from ``ConfigModelBase``.
            Can be used for default values storage. If config model is defined
            it will be initialised  from ``JSONDict`` configs if such is provided
            instead of config model instance.
        config: ``pydantic`` based or ``JSONDict`` component config.
    """
    config_model: Optional[TConfigModel] = None
    config: Optional[TConfig]

    # TODO: Think of more strict config validation.
    def __init__(self, config: Optional[TConfig] = None) -> None:
        """Initialises component config.

        Validates config model type and initialised component config:

        Args:
            config: ``pydantic`` based or ``JSONDict`` component config.
        """
        if not self.config_model:
            self.config = config
        else:
            if not issubclass(self.config_model, ConfigModelBase):
                raise TypeError('Config model should be a subclass of ComponentConfigBase')

            if isinstance(config, dict):
                self.config = self.config_model.parse_obj(config)
            elif config is None:
                self.config = self.config_model()
            else:
                self.config = config


TComponent = TypeVar('TComponent', bound=ComponentBase)


class State:
    """Represents state of any agent executing its behavior program.

    State contains both current behavior tree nodes statuses and arbitrary
    named variables values which can be read or modified either by any
    decision tree node or by means of communication of behavior agent
    with the external environment.

    Metaphorically, state represent snapshot of behavior agent consciousness
    in any given moment: it contains both inputs from the interaction with the
    external environment and results of these inputs processing.

    State variables are stored in the Dict which can be accessed through the
    ``vars`` property. Keys are variables names and values are variables values.
    There is an important project-wide convention: ``None`` state variable value
    always represents uninitialised variable.

    Also JSON is used as a default serialisation format in ``nodzz``, so all
    variable values are presumed to be JSON serializable. No actual type
    checking is implemented, though some default methods like conversion
    to/from dict are implemented in JSON friendly way. You can derive
    your own state from this class and implement it in the way appropriate
    to your project.
    """
    def __init__(self, uid: Optional[str] = None,
                 variables: Optional[Dict[str, JSONType]] = None,
                 nodes: Optional[Dict[str, NodeStatus]] = None) -> None:
        """Initialises state instance.

        State constructor is presumed to be used for blank state instance
        creation, so mostly you will not have to specify ``variables`` and
        ``nodes`` arguments. ``from_dict`` class method can be referred for
        these arguments usage.

        Args:
            uid: An optional str state unique id.
            variables: An optional dict with state variables value.
            nodes: An optional dict with state nodes statuses.
        """
        self._uid = uid
        self._vars = variables or {}
        self._nodes = nodes or {}

    @property
    def uid(self) -> Optional[str]:
        """An optional string unique id."""
        return self._uid

    @property
    def vars(self) -> JSONDict:
        """State variables dictionary."""
        return self._vars

    def to_dict(self, nodes: bool = False) -> JSONDict:
        """Converts state to its dict representation.

        Args:
            nodes: A boolean flag which includes nodes statuses into results.
                Since each node status is converted to the serialization friendly
                format, it can be some kind of expensive operation, so the default
                value of the flag is ``False``.

        Returns: Dict representation of the state.
        """
        result = {
            'uid': self._uid,
            'variables': self._vars
        }

        if nodes:
            result['nodes'] = {
                node: status.value for node, status in self._nodes.items() if status is not NodeStatus.READY
            }

        return result

    @classmethod
    def from_dict(cls, state_dict: JSONDict) -> 'State':
        """Initialises state from its dict representation.

        Args:
            state_dict: Dict representation of state.

        Returns:
            Instance of the State object.
        """
        uid = state_dict['uid']
        variables = state_dict['variables']
        nodes = {node: NodeStatus(status) for node, status in state_dict.get('nodes', {}).items()}
        return cls(uid=uid, variables=variables, nodes=nodes)

    def get_node_status(self, node_id: str) -> NodeStatus:
        """Returns status of a single node.

        Args:
            node_id: Str node id in behavior tree.

        Returns:
            Node status.
        """
        return self._nodes.get(node_id, NodeStatus.READY)

    def reset_node_status(self, node_id: str) -> None:
        """Resets single node status.

        Removes status of the single node from statuses dict which is equal
        to setting READY status to the node. Status removal (instead of READY
        assigning) allows to reduce amount of operations during state serialisation.

        Args:
            node_id: Str node id in behavior tree.
        """
        self._nodes.pop(node_id, None)

    def set_node_status(self, node_id: str, status: NodeStatus) -> None:
        """Sets single node status.

        Status removal (instead of READY assigning) allows to reduce amount
        of operations during state serialisation.

        Args:
            node_id: Str node id in behavior tree.
            status: Status assigned to the node.
        """
        if status is NodeStatus.READY:
            self.reset_node_status(node_id)
        else:
            self._nodes[node_id] = status

    def reset_nodes(self) -> None:
        """Resets statuses of ALL nodes for the state."""
        self._nodes = {}
