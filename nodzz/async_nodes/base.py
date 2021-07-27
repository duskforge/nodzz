"""Base classes for the asynchronous implementations of the main node types.

``nodzz`` allows to implement asynchronous behavior trees and provides asynchronous
API. Here are the basic rules and principles of ``nodzz`` asynchronous development:
    - Each asynchronous tree node should have an asynchronous ``execute`` method
        implementation (i.e., each node ``execute`` method should be coroutine,
        see this for further references: https://docs.python.org/3/library/asyncio-task.html#awaitables)
        or it should be asyncable.
    - Asynchronous controller nodes should be derived from ``AsyncControllerNodeBase``
        class (or have this class in their ancestors chain) and must have an
        asynchronous ``execute`` method implementation.
    - Asynchronous task nods can ether have an asynchronous ``execute`` method
        implementation or be asyncable. Please see ``NodeBase`` class documentation
        for the further asyncable nodes reference.
    - ``AsyncTree`` should be used as an asynchronous behavior tree entry point.
    - All main ``nodzz`` node types are planned to have both synchronous and
        asynchronous (or asyncable) implementations.
    - Usually asynchronous behavior trees are used for the microservice pattern
        implementation: tree itself acts as an orchestrator and its nodes implement
        only IO-bound tasks while heavy CPU-bound tasks are implemented in the
        microservices which are called by the corresponding nodes.
"""
# TODO: Some of the docstrings parts should be moved to docs.

from inspect import iscoroutinefunction
from typing import Optional

from nodzz.basic_types import NodeStatus
from nodzz.core import State
from nodzz.nodes.base import NodeWrapperBase, ControllerNodeBase, ControllerConfig, TControllerConfig, TNode


class AsyncNodeWrapper(NodeWrapperBase):
    """Asynchronous node wrapper implementation.

    See the base class for the reference.
    """
    def __init__(self, node: TNode) -> None:
        """Initialises node wrapper.

        Mirrors wrapped node ``execute`` method or wraps it up in the debug
        executor. Also handles async wrapping of asyncable nodes ``execute``
        methods.

        Args:
            node: Initialised node instance to be wrapped.
        """
        super().__init__(node=node)

        if not iscoroutinefunction(node.execute):
            if node.asyncable:
                if self._tree_debug:
                    self.execute = self._execute_sync_debug
                else:
                    self.execute = self._execute_sync
            else:
                raise AttributeError(f'{node.__class__.__name__} can not be used in asynchronous trees')

        elif self._tree_debug:
            self.execute = self._execute_sync_debug

    async def execute(self, state: State) -> NodeStatus:
        """Calls wrapped node ``execute`` method."""
        return await self._node.execute(state=state)

    async def _execute_sync(self, state: State) -> NodeStatus:
        """Synchronously calls wrapped node ``execute`` method."""
        return self._node.execute(state=state)

    async def _execute_async_debug(self, state: State) -> NodeStatus:
        """Executes node and calls logging of its execution status.

        Tree debug mode wrapper for the node ``execute`` method.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = await self._node.execute(state=state)
        self._log_debug(status=status, state=state)
        return status

    async def _execute_sync_debug(self, state: State) -> NodeStatus:
        """Version of the ``_execute_async_debug`` with the synchronous node execution call."""
        status = self._node.execute(state=state)
        self._log_debug(status=status, state=state)
        return status


class AsyncControllerNodeBase(ControllerNodeBase):
    """Base class for asynchronous controller nodes.

    See the base class for the reference.
    """
    config_model = ControllerConfig

    def __init__(self, *children: TNode, config: Optional[TControllerConfig] = None) -> None:
        """See the base class."""
        super().__init__(config=config)
        self.children = tuple(AsyncNodeWrapper(child) for child in children)

    async def execute(self, state: State) -> NodeStatus:
        """See the base class."""
        raise NotImplementedError
