"""Asynchronous controller nodes implementations."""

from nodzz.core import State
from nodzz.basic_types import NodeStatus
from nodzz.async_nodes.base import AsyncControllerNodeBase, TNode


class AsyncSelectorNode(AsyncControllerNodeBase):
    """Asynchronous implementation of the non-persistent selector node.

    See ``SelectorNode`` class for the reference.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    async def execute(self, state: State) -> NodeStatus:
        """See ``SelectorNode.execute`` method for the reference."""
        status = NodeStatus.FAILED

        for node in self.children:
            status = await node.execute(state)

            if status != NodeStatus.FAILED:
                break

        return status


class AsyncPersistentSelectorNode(AsyncControllerNodeBase):
    """Asynchronous implementation of the persistent selector node.

    See ``PersistentSelectorNode`` class for the reference.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    async def execute(self, state: State) -> NodeStatus:
        """See ``PersistentSelectorNode.execute`` method for the reference."""
        status = NodeStatus.FAILED

        for node in self.children:
            current_status = state.get_node_status(node_id=node.id)

            if current_status == NodeStatus.READY or current_status == NodeStatus.RUNNING:
                status = await node.execute(state)

            if status == NodeStatus.FAILED or status == NodeStatus.RUNNING:
                state.set_node_status(node_id=node.id, status=status)

            if status == NodeStatus.RUNNING or status == NodeStatus.SUCCESS:
                break

        if status == NodeStatus.SUCCESS or status == NodeStatus.FAILED:
            self.reset(state)

        return status


class AsyncSequenceNode(AsyncControllerNodeBase):
    """Asynchronous implementation of the non-persistent sequence node.

    See ``SequenceNode`` class for the reference.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    async def execute(self, state: State) -> NodeStatus:
        """See ``SequenceNode.execute`` method for the reference."""
        status = NodeStatus.SUCCESS

        for node in self.children:
            status = await node.execute(state)

            if status != NodeStatus.SUCCESS:
                break

        return status


class AsyncPersistentSequenceNode(AsyncControllerNodeBase):
    """Asynchronous implementation of the persistent sequence node.

    See ``PersistentSequenceNode`` class for the reference.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    async def execute(self, state: State) -> NodeStatus:
        """See ``PersistentSequenceNode.execute`` method for the reference."""
        status = NodeStatus.SUCCESS

        for node in self.children:
            current_status = state.get_node_status(node_id=node.id)

            if current_status == NodeStatus.READY or current_status == NodeStatus.RUNNING:
                status = await node.execute(state)

            if status == NodeStatus.SUCCESS or status == NodeStatus.RUNNING:
                state.set_node_status(node_id=node.id, status=status)

            if status == NodeStatus.RUNNING or status == NodeStatus.FAILED:
                break

        if status == NodeStatus.SUCCESS or status == NodeStatus.FAILED:
            self.reset(state)

        return status
