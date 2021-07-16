"""Controller nodes implementations."""
# TODO: Some of the docstrings parts should be moved to docs.

from nodzz.core import State
from nodzz.basic_types import NodeStatus
from nodzz.nodes.base import ControllerNodeBase, TNode


class SelectorNode(ControllerNodeBase):
    """Selector node finds (selects) its first child node that is executed without fail.

    Node sequentially executes its child nodes until one of them returns SUCCESS
    or RUNNING status. This implementation is NON-PERSISTENT, so when one of the
    nodes returns RUNNING status, child nodes statuses are not saved and RUNNING
    status is immediately returned. The next node execution starts with the first
    child node.

    When one of the child nodes returns SUCCESS status, the same status is immediately
    returned without further children nodes execution. When all of the child nodes
    return FAILED status, the same status is immediately returned.

    If child nodes priority among each other matters, it can be set by defining
    theirs execution order during selector node initialisation.

    Selector node behavior resembles OR logical gate and usually used to select
    one of possible behaviors.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    def execute(self, state: State) -> NodeStatus:
        """Executes its child nodes until one of them returns RUNNING or SUCCESS status.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = NodeStatus.FAILED

        for node in self.children:
            status = node.execute(state)

            if status != NodeStatus.FAILED:
                break

        return status


class PersistentSelectorNode(ControllerNodeBase):
    """Selector node finds (selects) its first child node that is executed without fail.

    Node sequentially executes its child nodes until one of them returns SUCCESS
    or RUNNING status. This implementation is PERSISTENT, so when one of the
    nodes returns RUNNING status, child nodes statuses are saved and RUNNING
    status is immediately returned. The next node execution starts with the
    running child node.

    When one of the child nodes returns SUCCESS status, the same status is immediately
    returned without further children nodes execution. When all of the child nodes
    return FAILED status, the same status is immediately returned.

    If child nodes priority among each other matters, it can be set by defining
    theirs execution order during selector node initialisation.

    Selector node behavior resembles OR logical gate and usually used to select
    one of possible behaviors.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    def execute(self, state: State) -> NodeStatus:
        """Executes its child nodes until one of them returns RUNNING or SUCCESS status.

        If child node returns RUNNING status all child nodes statuses are saved until
        next sequence node execution.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = NodeStatus.FAILED

        for node in self.children:
            current_status = state.get_node_status(node_id=node.id)

            if current_status == NodeStatus.READY or current_status == NodeStatus.RUNNING:
                status = node.execute(state)

            if status == NodeStatus.FAILED or status == NodeStatus.RUNNING:
                state.set_node_status(node_id=node.id, status=status)

            if status == NodeStatus.RUNNING or status == NodeStatus.SUCCESS:
                break

        if status == NodeStatus.SUCCESS or status == NodeStatus.FAILED:
            self.reset(state)

        return status


class SequenceNode(ControllerNodeBase):
    """Sequence node executes its child nodes until one of them is executed without success.

    Sequence Node sequentially executes its child nodes until one of them returns
    FAILED or RUNNING status. This implementation is NON-PERSISTENT, so when one
    of the nodes returns RUNNING status, child nodes statuses are not saved and
    RUNNING status is immediately returned without further children nodes execution.
    The next node execution starts with the first child node.

    When one of the child nodes returns FAILED status, the same status is immediately
    returned without further children nodes execution. When all of the child nodes
    return SUCCESS status, the same status is immediately returned.

    Children nodes execution order is defined during sequence node initialisation.

    Sequence node behavior resembles AND logical gate and usually used to encapsulate
    sequence of actions needed to perform some task.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    def execute(self, state: State) -> NodeStatus:
        """Executes its child nodes until one of them returns RUNNING or FAILED status.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = NodeStatus.SUCCESS

        for node in self.children:
            status = node.execute(state)

            if status != NodeStatus.SUCCESS:
                break

        return status


class PersistentSequenceNode(ControllerNodeBase):
    """Sequence node executes its child nodes until one of them is executed without success.

    Sequence Node sequentially executes its child nodes until one of them returns
    FAILED or RUNNING status. This implementation is PERSISTENT, so when one of the
    nodes returns RUNNING status, ALL child nodes statuses are saved and RUNNING
    status is immediately returned without further children nodes execution. The
    next node execution starts with the running child node.

    When one of the child nodes returns FAILED status, the same status is immediately
    returned without further children nodes execution. When all of the child nodes
    return SUCCESS status, the same status is immediately returned. In both of these
    cases all child nodes statuses will be reset.

    Children nodes execution order is defined during sequence node initialisation.

    Sequence node behavior resembles AND logical gate and usually used to encapsulate
    sequence of actions needed to perform some task.
    """
    def __init__(self, *children: TNode, config=None) -> None:
        """See the base class."""
        super().__init__(*children, config=config)

    def execute(self, state: State) -> NodeStatus:
        """Executes its child nodes until one of them returns RUNNING or FAILED status.

        If child node returns RUNNING status all child nodes statuses are saved until
        next sequence node execution.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        status = NodeStatus.SUCCESS

        for node in self.children:
            current_status = state.get_node_status(node_id=node.id)

            if current_status == NodeStatus.READY or current_status == NodeStatus.RUNNING:
                status = node.execute(state)

            if status == NodeStatus.SUCCESS or status == NodeStatus.RUNNING:
                state.set_node_status(node_id=node.id, status=status)

            if status == NodeStatus.RUNNING or status == NodeStatus.FAILED:
                break

        if status == NodeStatus.SUCCESS or status == NodeStatus.FAILED:
            self.reset(state)

        return status
