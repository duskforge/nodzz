## v0.1.0

Noddz first release

* **Added** component entity (`ComponentBase`).
* **Added** base `pdantic` model for component configs (`ConfigModelBase`). 
* **Added** state entity (`State`).
* **Added** node (`NodeBase`) and controller node (`ControllerNodeBase`) entities.
* **Added** implementations of the core controller node types: selector node (`SelectorNode`, `PersistentSelectorNode`),
  sequence node (`SequenceNode`, `PersistentSequenceNode`).
* **Added** implementations of typical task nodes: `EvaluationNode`, `EvalNoneNode`, `AssignNode`, `ResetNode`.
* **Added** component configs container implementation (`ConfigSet`) and single config file parsing method (`load_config_file`).
* **Added** behavior tree entry point implementation (`Tree`).