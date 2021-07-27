"""Typical task nodes implementations."""
# TODO: Some of the docstrings parts should be moved to docs.

from collections import defaultdict
from functools import partial
from typing import List, Union, Optional, TypeVar, Dict

from pydantic import BaseModel, validator, Field

from nodzz.basic_types import JSONSimpleType, JSONType, NodeStatus
from nodzz.core import ConfigModelBase, State
from nodzz.nodes.base import NodeBase

_EvalArgs = Union[List[JSONSimpleType], float, int, bool, str]
_EvalArgsNone = Union[_EvalArgs, None]


class EvalSettingsBase(BaseModel):
    """Base model for evaluation settings.

    Attributes:
        eval_type: Str evaluation type identifier, its constant default value must be
            set in subclasses.
        invert: Boolean inversion flag. If ``True``, ``not`` operator is applied to the
            evaluation result
    """
    eval_type: str
    invert: bool = False

    @validator('eval_type')
    def match_eval_type(cls, v: str) -> str:
        """Validates evaluation type name.

        Method is used for validation during config initialisation from
        JSON-like dicts by ``parse_obj`` method. Ensures proper evaluation
        settings initialisation.

        Args:
            v: Str ``eval_type`` field value.

        Returns:
            Unchanged str ``eval_type`` field value.
        """
        eval_type = cls.__fields__['eval_type'].default

        if v != eval_type:
            raise ValueError(f'Not valid evaluation type \'{v}\', should be \'{eval_type}\'')

        return v


class Equal(EvalSettingsBase):
    """'Is equal' evaluation config model.

    Configures evaluation: if variable value is equal to the given value.

    Attributes:
        value: Value to be compared with variable value.
    """
    eval_type: str = Field(default='equal', const=True)
    value: _EvalArgs


class More(EvalSettingsBase):
    """'Is more' evaluation config model.

    Configures evaluation: if variable value is more then the given value.

    Attributes:
        value: Value to be compared with variable value.
        strict: Boolean comparison type. If ``True`` - strict comparison will be
            applied, if ``False`` - not strict.
    """
    eval_type: str = Field(default='more', const=True)
    value: Union[int, float]
    strict: bool = True


class Less(EvalSettingsBase):
    """'Is less' evaluation config model.

    Configures evaluation: if variable value is less then the given value.

    Attributes:
        value: Value to be compared with variable value.
        strict: Boolean comparison type. If ``True`` - strict comparison will be
            applied, if ``False`` - not strict.
    """
    eval_type: str = Field(default='less', const=True)
    value: Union[int, float]
    strict: bool = True


class Intersection(EvalSettingsBase):
    """'Lists intersection' evaluation config model.

    Configures evaluation: if list from variable value has at least one element
    in common with the given list.

    Attributes:
        value: Value to be compared with variable value.
    """
    eval_type: str = Field(default='intersection', const=True)
    value: List[JSONSimpleType]


_SingleEvaluation = Union[Equal, More, Less, Intersection]
_Evaluation = Union[_SingleEvaluation, List[_SingleEvaluation]]


class EvaluationNodeConfig(ConfigModelBase):
    """Base model for the ``EvaluationNode`` settings.

    Every ``EvaluationNode`` config should be derived from this class. Each
    variable value evaluation is configured by an item of the ``conditions``
    field dict, where string key is equal to the evaluated variable name
    and value has two possible type options:
    1. One of ``EvalSettingsBase`` subclasses (but not the ``EvalSettingsBase``
        itself). In this case only one variable evaluation will be performed
        according to the evaluation type and values it was initialised with.
    2. List of ``EvalSettingsBase`` subclasses. In this case each defined
        evaluation will be performed for the variable.

    Attributes:
        conditions: Dict with evaluation conditions.
        eval_none: Bool uninitialised values evaluation flag. If ``True``
            uninitialised variables (which are equal to variables with
            ``None`` values) will be estimated. If ``False``, node will return
            RUNNING status until all variables will be initialised or
            at least one evaluation fails.
    """
    conditions: Dict[str, _Evaluation]
    eval_none: bool = False


TEvaluationNodeConfig = TypeVar('TEvaluationNodeConfig', bound=EvaluationNodeConfig)


class EvaluationNode(NodeBase):
    """Node that evaluates state variables values.

    This node implements one of the most common tasks: check if some state
    variables values meet certain conditions. ``EvaluationNode`` allows to
    parametrise all variables values evaluations in node config, so its
    enough to create new config by deriving from ``EvaluationNodeConfig``
    and initialise node with it. Also ``EvaluationNode`` can be configured
    by ``JSONDict`` config. In this case no special config model should be
    created, but config should match ``EvaluationNodeConfig`` config model.

    Four most common evaluation operation are implemented, see methods
    with ``eval_`` prefix.
    """
    asyncable: bool = True
    config_model = EvaluationNodeConfig
    config: TEvaluationNodeConfig

    def __init__(self, config: Optional[TEvaluationNodeConfig] = None) -> None:
        """See the base class."""
        super().__init__(config=config)
        self._evaluations_map = defaultdict(list)
        conditions = self.config.conditions

        for var, evaluations in conditions.items():
            evaluations = evaluations if isinstance(evaluations, list) else [evaluations]

            for evaluation in evaluations:
                eval_dict = evaluation.dict()
                method_name = f'eval_{eval_dict.pop("eval_type")}'
                method = getattr(self, method_name)
                invert = eval_dict.pop('invert')
                handler = partial(method, **eval_dict)

                if invert:
                    def not_handler(value):
                        return not handler(value)
                    self._evaluations_map[var].append(not_handler)
                else:
                    self._evaluations_map[var].append(handler)

    def execute(self, state: State) -> NodeStatus:
        """Evaluates state variables.

        Returns SUCCESS status if all evaluations were successfully passed for all
        variables. Otherwise it returns:
        - FAILED status if at least one of the evaluations failed or at least one
            variable was not initialised and ``eval_none`` config flag is ``True``;
        - RUNNING status if ``eval_none`` config flag is ``False``, at least one variable
            being estimated is not initialised and ``None`` evaluations failed.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        result = NodeStatus.SUCCESS

        for var, evaluations in self._evaluations_map.items():
            value = state.vars.get(var)

            if value is None:
                if self.config.eval_none:
                    return NodeStatus.FAILED
                else:
                    result = NodeStatus.RUNNING
            else:
                for eval_handler in evaluations:
                    if not eval_handler(value):
                        return NodeStatus.FAILED

        return result

    @staticmethod
    def eval_equal(var: _EvalArgs, value: _EvalArgs) -> bool:
        """Evaluates if variable value is equal to the given value.

        Args:
            var: Value of the variable being evaluated.
            value: Value to compare.
        Returns:
            ``True`` if variable value is equal to the given value, else ``False``.
        """
        return var == value

    @staticmethod
    def eval_more(var: Union[int, float], value: Union[int, float], strict: bool = True) -> bool:
        """Evaluates if variable value is more then the given value.

        Args:
            var: Value of the variable being evaluated.
            value: Value to compare.
            strict: Strict comparison flag, if ``True`` - strict comparison is performed.
        Returns:
            ``True`` if variable value is more than the given value, else ``False``.
        """
        return var > value if strict else var >= value

    @staticmethod
    def eval_less(var: Union[int, float], value: Union[int, float], strict: bool = True) -> bool:
        """Evaluates if variable value is less then the given value.

        Args:
            var: Value of the variable being evaluated.
            value: Value to compare.
            strict: Strict comparison flag, if ``True`` - strict comparison is performed.
        Returns:
            ``True`` if variable value is less than the given value, else ``False``.
        """
        return var < value if strict else var <= value

    @staticmethod
    def eval_intersection(var: List[JSONSimpleType], value: List[JSONSimpleType]) -> bool:
        """Evaluates if list from variable value has at least one element in common with the given list.

        Elements order does not affect evaluation result, as it was checked two
        unordered sets intersection.

        Args:
            var: List variable value.
            value: List to search common elements with.
        Returns:
            ``True`` if list from variable value has at least one element in common
            with the given list, else ``False``.
        """
        return bool(set(var).intersection(set(value)))


class EvalNoneNodeConfig(ConfigModelBase):
    """Base model for the ``EvalNoneNode`` settings.

    Attributes:
        variables: List of str names of the variables to be evaluated to be initialised.
        invert: Boolean inversion flag. If ``True``, ``not`` operator is applied to the
            each variable evaluation result
    """
    variables: List[str] = Field(min_items=1)
    invert: bool = False


class EvalNoneNode(NodeBase):
    """Node that evaluates if state variables initialised.

    This node implements one of the most common tasks: check if some
    state variables values initialised. Please note that there is an
    important project-wide convention: ``None`` state variable value
    always represents uninitialised variable.
    """
    asyncable: bool = True
    config_model = EvalNoneNodeConfig
    config: EvalNoneNodeConfig

    def __init__(self, config: Optional[EvalNoneNodeConfig] = None) -> None:
        super().__init__(config=config)

    def execute(self, state: State) -> NodeStatus:
        """Evaluates if state variables initialised.

        If ``invert`` config flag is ``False`` returns FAILED status if at least one of the
        evaluated variables is uninitialised or is ``None``. Otherwise returns SUCCESS status.

        If ``invert`` config flag is ``True`` returns FAILED status if at least one of the
        evaluated variables is initialised and not ``None``. Otherwise returns SUCCESS status.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        if self.config.invert:
            for var in self.config.variables:
                if state.vars.get(var) is None:
                    return NodeStatus.FAILED
        else:
            for var in self.config.variables:
                if state.vars.get(var) is not None:
                    return NodeStatus.FAILED

        return NodeStatus.SUCCESS


class AssignNodeConfig(ConfigModelBase):
    """Base model for the ``SetNode`` settings.

    Every ``AssignNode`` config should be derived from this class. Each assignment
    of a value to a state variable is configured by an item of the ``assignments``
    field dict, where string key is equal to the variable name and value is
    assigned value.

    Attributes:
        assignments: Dict with variable naes and assigned values.
    """
    assignments: Dict[str, JSONType]


TAssignNodeConfig = TypeVar('TAssignNodeConfig', bound=AssignNodeConfig)


class AssignNode(NodeBase):
    """Node that assigns values to the state variables.

    ``AssignNode`` allows to parametrise all assignments of values to state variables,
    so its enough to create new config by deriving from ``AssignNodeConfig`` and
    initialise node with it. Also ``EvaluationNode`` can be configured by ``JSONDict``
    config. In this case no special config model should be created, but config should
    match ``AssignNodeConfig`` config model.
    """
    asyncable: bool = True
    config_model = AssignNodeConfig
    config: TAssignNodeConfig

    def __init__(self, config: Optional[TAssignNodeConfig] = None) -> None:
        """See the base class."""
        super().__init__(config=config)

    def execute(self, state: State) -> NodeStatus:
        """Assigns values to the state variables according to the config settings.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """
        for var, value in self.config.assignments.items():
            state.vars[var] = value

        return NodeStatus.SUCCESS


class ResetNodeConfig(ConfigModelBase):
    """Base model for the ``ResetNode`` settings.

    Attributes:
        variables: ``None`` or list of str names of the variables to be reset.
            If empty list or ``None``, ALL variables will be rest.
    """
    variables: Optional[List[str]] = Field(default=None)


class ResetNode(NodeBase):
    """Node that resets state valuables."""
    asyncable: bool = True
    config_model = ResetNodeConfig
    config: ResetNodeConfig

    def __init__(self, config: Optional[EvalNoneNodeConfig] = None) -> None:
        super().__init__(config=config)

    def execute(self, state: State) -> NodeStatus:
        """Resets state variables according to the config settings.

        Deletes items with keys given in config from the state variables dict.
        If variables names list in config is empty or ``None``, ALL variables will
        be deleted.

        Args:
            state: Behavior tree execution state.

        Returns:
            One of three node execution statuses: SUCCESS, FAILED, RUNNING.
        """

        if self.config.variables:
            for var in self.config.variables:
                state.vars.pop(var, None)
        else:
            state.vars.clear()

        return NodeStatus.SUCCESS
