"""Base classes for the main node types."""
# TODO: Some of the docstrings parts should be moved to docs.

from os import getenv
from typing import TypeVar, Optional, List

from nodzz.basic_types import NodeStatus
from nodzz.core import ConfigModelBase, ComponentBase, State, TConfig

_tree_debug_env = getenv('NODZZ_TREE_DEBUG')
_tree_debug = True if _tree_debug_env == '1' else False


class NodeBase(ComponentBase):
    """Base class for the node entity.

    Node is the main (and only) building block of behavior trees. In most
    cases each node performs some of these tasks when executed:
    - Control execution of other nodes (controller nodes);
    - Get information from external environment;
    - Update or modify state variables;
    - Estimate state variables;
    - Affect external environment.

    All nodes implementations or other nodes abstractions (except controller
    nodes) should derive from this class.

    Attributes:
        asyncable: Bool `asyncio` compatibility flag. If ``True`` and node ``execute``
            method is not defined as ``async``, it will be automatically wrapped to
            the coroutine during asynchronous behavior tree initialisation. Otherwise
            exception will be risen if synchronous node will tried to be used in
            asynchronous tree. Such behavior is implemented to allow synchronous nodes
            be reused in asynchronous trees. Please be cautious with this flag and set
            it to ``True`` only when implementing nodes with non CPU-bound ``execute``
            method.
    """
    asyncable: bool = False

    def __init__(self, config: Optional[TConfig] = None) -> None:
        """See the base class."""
        super().__init__(config=config)

    def execute(self, state: State) -> NodeStatus:
        """Executes node.

        When implemented, method executes node logic and returns its execution
        status:
        - SUCCESS status means that the node successfully performed its task;
        - FAILED status means that the node was not able to perform its task
            successfully. Either because of behavior agent internal or external
            environment state or because of application internal error.
        - RUNNING status that the node currently performing some actions (or
            awaiting something) to return SUCCESS or FAILED status further.
            RUNNING status interpretation depends of the internal logic of the
            entity which controls execution of the node which returned this
            status.

        The fact, that the final node execution status is either SUCCESS or FAILED,
        allows to consider any node as a logical gate that affects decision tree
        execution.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        raise NotImplementedError

    def prepare(self, node_id: str) -> None:
        """Method is implemented in ``NodeWrapper`` and ``ControllerNodeBase`` classes
        and resides here for API compatibility.
        """
        pass

    def reset(self, state: State) -> None:
        """Method is implemented in ``NodeWrapper`` and ``ControllerNodeBase`` classes
        and resides here for API compatibility.
        """
        pass


TNode = TypeVar('TNode', bound=NodeBase)


class NodeWrapperBase(NodeBase):
    """Node wrapping container.

    Each initialised node is wrapped to this container before it is allocated
    to its position in the behavior tree. The may reason for this is that
    each node is identified by its position in the tree and sometimes the
    same initialised behavior should be executed from the different nodes of
    the tree.

    So when we put one initialised node (functional instance) in several
    places (logical nodes) in the tree, several NodeWrapper instances are
    created (each instance for an each logical node). Each wrapper executes
    the same functional instance but handles execution statuses according
    its position in the tree.

    NodeWrapper mirrors standard Node API.
    """
    def __init__(self, node: TNode) -> None:
        """Initialises node wrapper.

        Args:
            node: Initialised node instance to be wrapped.
        """
        super().__init__(config=node.config)
        self.id: Optional[str] = None
        self._node = node
        self._tree_debug = _tree_debug

    def execute(self, state: State) -> NodeStatus:
        """Calls wrapped node ``execute`` method."""
        raise NotImplementedError

    # TODO: Refactor, use logging.
    def _log_debug(self, status: NodeStatus, state: State) -> None:
        """Logs node execution status and behavior tree state after node execution.

        Args:
            status: Node execution status.
            state: Behavior tree execution state.
        """
        state_str = str(state.to_dict())
        config_dict = dict(self.config)
        name = config_dict.get('name')
        debug_str = f'[nodzz debug] id: {self.id}, name: {name}, status: {str(status)}, state: {state_str}'
        print(debug_str)

    def prepare(self, node_id: str) -> None:
        """Sets node id.

        Also calls wrapped node ``prepare`` method. If this is controller node,
        all child nodes ``prepare`` methods will be subsequently called.

        Args:
            node_id: String node id.
        """
        self.id = node_id
        self._node.prepare(node_id)

    def reset(self, state: State) -> None:
        """Resets node status.

        Sets node status to READY. Also calls wrapped node ``reset`` method.
        If this is controller node, all child nodes statuses will be
        subsequently reset.

        Args:
            state: Behavior tree execution state.
        """
        state.reset_node_status(node_id=self.id)
        self._node.reset(state)


class NodeWrapper(NodeWrapperBase):
    """Synchronous node wrapper implementation.

    For more reference see the base class.
    """
    def __init__(self, node: TNode) -> None:
        """Initialises node wrapper.

        Mirrors wrapped node ``execute`` method or wraps it up in the debug
        executor.

        Args:
            node: Initialised node instance to be wrapped.
        """
        super().__init__(node=node)

        if self._tree_debug:
            self.execute = self._execute_debug

    def execute(self, state: State) -> NodeStatus:
        """Calls wrapped node ``execute`` method."""
        return self._node.execute(state=state)

    def _execute_debug(self, state: State) -> NodeStatus:
        """Executes node and calls logging of its execution status.

        Tree debug mode wrapper for the node ``execute`` method.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = self._node.execute(state=state)
        self._log_debug(status=status, state=state)
        return status


class ControllerConfig(ConfigModelBase):
    children: List[str] = []


TControllerConfig = TypeVar('TControllerConfig', bound=ControllerConfig)


class ControllerNodeBase(NodeBase):
    """Base class for control flow (controller) nodes.

    Controller nodes serve as a containers for another nodes (children nodes)
    and have one main purpose: control execution of its child nodes. Each time
    control node is executed, it either decides to execute one or several of its
    child nodes or to return its own execution status to its parent (another
    control node). In fact, this way control nodes implement branching in
    behavior trees. There are two base concepts, which form control nodes
    execution mechanism: Child nodes execution order and child nodes execution
    statuses.

    Each controller node is initialised with an ORDERED set of its children.
    That means that every initialised controller is always given the default order
    of its child nodes execution, though some controller node implementations
    can deliberately ignore this order.

    This concept maps on rational beings (both natural and artificial) behavior
    pattern: every rational being tends to prioritize its goals (and, as a result,
    behaviors aimed to achieve them). And every rational being tends to prioritize
    actions aimed to achieve any of its goals.

    Also control node does not supposed to have access to behavior state and makes
    decision about its next action based only on its already executed child nodes
    statuses. That means that agent behaviors stay fully encapsulated in nodes
    (non-controller) while decision making process is moved to the tree structure.
    This allows to easily add or remove nodes to the tree and simplifies subtrees
    reusing.

    All control nodes implementations or other control nodes abstractions should
    derive from this class.

    Attributes:
        children: Tuple of node wrappers with initialised child nodes.
    """
    config_model = ControllerConfig

    # TODO: Think of unifying __init__ signature among all components.
    def __init__(self, *children: TNode, config: Optional[TControllerConfig] = None) -> None:
        """Initialises controller node.

        Args:
            *children: Initialised child nodes.
            config: Pydantic BaseSettings node config.
        """
        super().__init__(config=config)
        self.children = tuple(NodeWrapper(child) for child in children)

    def execute(self, state: State) -> NodeStatus:
        """Method should implement execution logic of control node child nodes.

        Attention! Child nodes statuses management should be also implemented here.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        raise NotImplementedError

    def prepare(self, node_id: str) -> None:
        """Assigns ids to the children nodes.

        Args:
            node_id: String node id.
        """
        for i, child in enumerate(self.children):
            child_id = f'{node_id}.{i}'
            child.prepare(node_id=child_id)

    def reset(self, state: State) -> None:
        """Resets children nodes states.

        Args:
            state: Behavior tree execution state.
        """
        for child in self.children:
            child.reset(state)
