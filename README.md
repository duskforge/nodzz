[![PyPI](https://img.shields.io/pypi/v/nodzz)](https://pypi.python.org/pypi/nodzz)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nodzz)](https://www.python.org)
[![GitHub](https://img.shields.io/github/license/duskforge/nodzz)](https://github.com/duskforge/nodzz/blob/main/LICENSE)

# Nodzz: pure Python behavior trees framework

Nodzz is a Python open-source library which provides a framework for behavior trees creation and management. You can use
it to implement behavior of your Arduino based robot, chat-bot or whatever else has its own behavior.

## Key features

* Nodzz provides implementations of typical behavior trees components (like selector and sequence nodes) and base classes 
  for creating your own;
* Behavior trees can be assembled and configured from components by using Python API or
  [pydantic](https://pydantic-docs.helpmanual.io/) and JSON friendly configs;
* Supports both synchronous and asynchronous development.
  
## Future plans

* Documentation and tutorials will be available soon. For now, you can refer docstrings: [state and components](nodzz/core.py),
  [nodes base classes](nodzz/nodes/base.py), [controller nodes implementations](nodzz/nodes/controllers.py),
  [task nodes implementations](nodzz/nodes/tasks.py), [configuration](nodzz/config.py), [tree management](nodzz/tree.py)
  and [asynchronous development](nodzz/async_nodes/base.py).
* Graphic behavior trees design tool is planned to be implemented.
* The current set of implemented nodes (both controllers and tasks) is not final, more nodes implementations will be constantly
  added.
  

## Tutorial

### Installation

```
pip install nodzz
```

### Theory 

Behavior tree is a model of process execution planning. It is mainly applied in robotics and gaming AI. Here are some
references for understanding behavior trees basics:
[Wikipedia article](https://en.wikipedia.org/wiki/Behavior_tree_(artificial_intelligence,_robotics_and_control)) and
[Introduction to Behavior Trees by Björn Knafla](https://web.archive.org/web/20131209105717/http://www.altdevblogaday.com/2011/02/24/introduction-to-behavior-trees/).

From here on, we assume that you are familiar with behavior tree core concepts. Also, here is Nodzz terms agreement: 
* **Controller node** - a standard name for control flow nodes;
* **Task node** - a standard name for leaf nodes;
* **Behavior agent** - an entity which behavior is programmed by behavior tree;
* **State** - set of variables which represents snapshot of behavior agent "consciousness" in any given moment: it contains
  both inputs from the interaction with the external environment and results of these inputs processing.

### Basic Use

Let's fast forward 40k years and imagine distant planet where one imperial guardsman is serving his dangerous duty of
defending the Imperium of Man from its numerous enemies. We will try to model his behavior with Nodzz behavior tree.

Our brave guardsman behavior depends on number of enemies he encounters:
* No (zero) enemies: he will continue watching;
* One enemy: he will ruthlessly fight it;
* Many (more than one) enemies: hi will bravely run away (into the warm embraces of Commissar).

Once we described guardsman behavior model, we can start implementing it in behavior tree.

We must first determine how our character interacts with the external environment. In this particular case he will be
awaiting only one input: enemies number. This is the only parameter affecting guardsman behavior. Let's create node which
reads enemies number from the command prompt and writes it to the state variable:

All necessary imports:

```
from nodzz.core import State
from nodzz.nodes.base import NodeBase, NodeStatus
from nodzz.nodes.controllers import SelectorNode, SequenceNode
from nodzz.nodes.tasks import EvaluationNode, EvaluationNodeConfig, More, Less, Equal
```

Command prompt reading node:

```
class InputNode(NodeBase):
    """Initialises node.

    Args:
          config: A dict with the following template: {'enemies_num_var': <state_variable_name>}.
    """
    def __init__(self, config):
        super().__init__(config=config)

    def execute(self, state):
        input_str = input('\nType enemies number or "exit" for exit: ')

        # Graceful exit
        if input_str == 'exit':
            exit()

        # Parsing input
        if input_str.isnumeric():
            input_int = int(input_str)
        else:
            input_int = 0  # Default value for any non-numeric input.

        state.vars[self.config['enemies_num_var']] = input_int

        # execute() method should ALWAYS return node NodeStatus
        return NodeStatus.SUCCESS
```

Also, our guardsman needs to notice his external environment (in this particular case - us) about the decisions he makes.
We will create simple node which prints a text that was set in its config:

```
class OutputNode(NodeBase):
    def __init__(self, config):
        """Initialises node.

        Args:
              config: A dict with the following template: {'output': <text_that_node_instance_will_print>}.
        """
        super().__init__(config=config)

    def execute(self, state):
        print(self.config['output'])

        return NodeStatus.SUCCESS
```

Let's set name of the state variable where number of detected enemies will be stored:

```
var_name = 'enemies_num'
```

Each behavior scenario of the guardsman will be a sequence of two actions: 1. Estimate enemies number; 2. Tell us about
the decision he made.

Enemies number estimation will be implemented by initialising of properly configured `EvaluationNode`. Evaluation node
implements one of the typical decision tree tasks: state variable value evaluation. It allows setting basic evaluation
operation with config without any additional code writing. Notification will be implemented via `OutputNode`. The whole
behavior scenario (branch) will be implemented as an instance of `SequenceNode` initialised with the instances of `EvaluationNode`
and `OutputNode` given in the order of their execution.

Zero enemies scenario implementation:

```
zero_enemies_check_cfg = EvaluationNodeConfig(conditions={var_name: Less(value=1)})
zero_enemies_check = EvaluationNode(config=zero_enemies_check_cfg)
zero_enemies_behavior = OutputNode(config={'output': 'No enemies detected, keeping watching.'})
zero_enemies_sequence = SequenceNode(zero_enemies_check, zero_enemies_behavior)
```

One enemy scenario implementation:

```
one_enemy_check_cfg = EvaluationNodeConfig(conditions={var_name: Equal(value=1)})
one_enemy_check = EvaluationNode(config=one_enemy_check_cfg)
one_enemy_behavior = OutputNode(config={'output': 'An enemy detected, fight!'})
one_enemy_sequence = SequenceNode(one_enemy_check, one_enemy_behavior)
```

Many enemies scenario implementation:

```
many_enemies_check_cfg = EvaluationNodeConfig(conditions={var_name: More(value=1)})
many_enemies_check = EvaluationNode(config=many_enemies_check_cfg)
many_enemies_behavior = OutputNode(config={'output': 'Many enemies detected, run away!'})
many_enemies_sequence = SequenceNode(many_enemies_check, many_enemies_behavior)
```

All initialised scenarios nodes will be composed in the scenario selector - an instance of `SelectorNode`. We will need
to fill enemies number state variable before starting traversing scenarios, so the root node of the guardsman behavior
tree will be `SequenceNode` instance initialised with the scenario selector instance `InputNode` instance given in the
order of their execution.

```
behavior_selector = SelectorNode(zero_enemies_sequence, one_enemy_sequence, many_enemies_sequence)
input_node = InputNode(config={'enemies_num_var': var_name})
root_sequence = SequenceNode(input_node, behavior_selector)
```

There are some final steps to finish behavior tree initialisation, get state instance and start tree execution:

```
root_sequence.prepare(node_id='root')
new_state = State()

while True:
    root_sequence.execute(state=new_state)
```

The whole snippet will be (this script is complete, it should run "as is"):

```
from nodzz.core import State
from nodzz.nodes.base import NodeBase, NodeStatus
from nodzz.nodes.controllers import SelectorNode, SequenceNode
from nodzz.nodes.tasks import EvaluationNode, EvaluationNodeConfig, More, Less, Equal


class InputNode(NodeBase):
    """Initialises node.

    Args:
          config: A dict with the following template: {'enemies_num_var': <state_variable_name>}.
    """
    def __init__(self, config):
        super().__init__(config=config)

    def execute(self, state):
        input_str = input('\nType enemies number or "exit" for exit: ')

        # Graceful exit
        if input_str == 'exit':
            exit()

        # Parsing input
        if input_str.isnumeric():
            input_int = int(input_str)
        else:
            input_int = 0  # Default value for any non-numeric input.

        state.vars[self.config['enemies_num_var']] = input_int

        # execute() method should ALWAYS return node NodeStatus
        return NodeStatus.SUCCESS


class OutputNode(NodeBase):
    def __init__(self, config):
        """Initialises node.

        Args:
              config: A dict with the following template: {'output': <text_that_node_instance_will_print>}.
        """
        super().__init__(config=config)

    def execute(self, state):
        print(self.config['output'])

        return NodeStatus.SUCCESS


var_name = 'enemies_num'


zero_enemies_check_cfg = EvaluationNodeConfig(conditions={var_name: Less(value=1)})
zero_enemies_check = EvaluationNode(config=zero_enemies_check_cfg)
zero_enemies_behavior = OutputNode(config={'output': 'No enemies detected, keeping watching.'})
zero_enemies_sequence = SequenceNode(zero_enemies_check, zero_enemies_behavior)

one_enemy_check_cfg = EvaluationNodeConfig(conditions={var_name: Equal(value=1)})
one_enemy_check = EvaluationNode(config=one_enemy_check_cfg)
one_enemy_behavior = OutputNode(config={'output': 'An enemy detected, fight!'})
one_enemy_sequence = SequenceNode(one_enemy_check, one_enemy_behavior)

many_enemies_check_cfg = EvaluationNodeConfig(conditions={var_name: More(value=1)})
many_enemies_check = EvaluationNode(config=many_enemies_check_cfg)
many_enemies_behavior = OutputNode(config={'output': 'Many enemies detected, run away!'})
many_enemies_sequence = SequenceNode(many_enemies_check, many_enemies_behavior)

behavior_selector = SelectorNode(zero_enemies_sequence, one_enemy_sequence, many_enemies_sequence)
input_node = InputNode(config={'enemies_num_var': var_name})
root_sequence = SequenceNode(input_node, behavior_selector)

root_sequence.prepare(node_id='root')
new_state = State()

while True:
    root_sequence.execute(state=new_state)
```

The result will be:

```
Type enemies number or "exit" for exit: 0
No enemies detected, keeping watching.

Type enemies number or "exit" for exit: 1
An enemy detected, fight!

Type enemies number or "exit" for exit: 2
Many enemies detected, run away!
```