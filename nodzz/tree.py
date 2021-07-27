"""Behavior tree management instruments."""

from typing import Optional, Dict, Union, Type

from nodzz.async_nodes.base import AsyncNodeWrapper
from nodzz.basic_types import NodeStatus
from nodzz.config import ConfigSet
from nodzz.core import State
from nodzz.nodes.base import TNode, NodeWrapperBase, NodeWrapper, NodeBase, ControllerNodeBase
from nodzz.utils import import_by_name


def _make_tree(config_set: ConfigSet, node_name: str, nodes: Optional[Dict[str, TNode]] = None) -> NodeBase:
    """Makes behavior tree.

    Recursively initialises nodes and composes behavior tree from them.

    Args:
        config_set: ConfigSet instance with tree nodes config.
        node_name: Str name of the behavior tree root node.
        nodes: Dict with initialised nodes instances. Keys are nodes names,
            values are nodes instances. Used for accessing already initialised
            nodes throughout function recursive calls to prevent repeated
            initialisations of the same node. Should be ``None`` when the
            method is called not from itself.

    Returns:
        Initialised behavior tree inside its root node. Root node returned
        without node wrapper.
    """
    nodes = nodes or {}
    result = nodes.get(node_name)

    if not result:
        config = config_set.get_config(node_name)
        class_name = config['class_name']
        node_class = import_by_name(class_name)

        if issubclass(node_class, ControllerNodeBase):
            children = [_make_tree(config_set, node_name, nodes) for node_name in config['children']]
            result = node_class(*children, config=config)
        elif issubclass(node_class, NodeWrapperBase):
            raise TypeError(f'Node wrapper can not be used as node class')
        elif issubclass(node_class, NodeBase):
            result = node_class(config=config)
        else:
            raise TypeError(f'Wrong component type: {class_name}, only NodeBase subclasses allowed')

        nodes[node_name] = result

    return result


class _TreeBase:
    """Base class for the behavior tree entry point.

    Tree handles behavior tree (re)initialisation and provides entry point
    for its execution.
    """
    def __init__(self, config_set: ConfigSet, wrapper_class: Type[Union[NodeWrapper, AsyncNodeWrapper]]) -> None:
        """Initialises behavior tree entry point.

        Args:
            config_set: ConfigSet with behavior tree nodes configs.
        """
        self._config_set = config_set
        self._config_set.resolve_configs()
        self._wrapper_class = wrapper_class
        self._root_node: Optional[Union[NodeWrapper, AsyncNodeWrapper]] = None

    def init_tree(self, node_name: str) -> None:
        """Initialises behavior tree.

        Deinitialises previously initialised tree if such exists.

        Args:
            node_name: Str name of the behavior tree root node.
        """
        del self._root_node
        root_node = _make_tree(config_set=self._config_set, node_name=node_name)
        self._root_node = self._wrapper_class(root_node)
        self._root_node.prepare(node_id='0')

    def execute(self, state: State) -> NodeStatus:
        """Executes behavior tree root node.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node statuses: SUCCESS, FAILED, RUNNING.
        """
        raise NotImplementedError


class Tree(_TreeBase):
    """Synchronous behavior tree entry point."""
    def __init__(self, config_set: ConfigSet) -> None:
        """See the base class."""
        super().__init__(config_set=config_set, wrapper_class=NodeWrapper)

    def execute(self, state: State) -> NodeStatus:
        """See the base class."""
        return self._root_node.execute(state)


class AsyncTree(_TreeBase):
    """Asynchronous behavior tree entry point."""
    def __init__(self, config_set: ConfigSet) -> None:
        """See the base class."""
        super().__init__(config_set=config_set, wrapper_class=AsyncNodeWrapper)

    async def execute(self, state: State) -> NodeStatus:
        """See the base class."""
        return await self._root_node.execute(state)
