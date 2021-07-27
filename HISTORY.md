## v0.2.0 (2021-07-28)
* **Fixed** snippets formatting in docstrings.
* **Added** classifiers to the `setup.cfg` `metadata` section.
* **Added** shields to readme.
* **Added** asynchronous API.

## v0.1.1 (2021-07-19)
* **Fixed** package discovery in `setup.cfg`.
* **Fixed** naming typos in docs.
* **Fixed** installation snippet in readme.

## v0.1.0 (2021-07-16)

Nodzz first release

* **Added** component entity (`ComponentBase`).
* **Added** base `pdantic` model for component configs (`ConfigModelBase`). 
* **Added** state entity (`State`).
* **Added** node (`NodeBase`) and controller node (`ControllerNodeBase`) entities.
* **Added** implementations of the core controller node types: selector node (`SelectorNode`, `PersistentSelectorNode`),
  sequence node (`SequenceNode`, `PersistentSequenceNode`).
* **Added** implementations of typical task nodes: `EvaluationNode`, `EvalNoneNode`, `AssignNode`, `ResetNode`.
* **Added** component configs container implementation (`ConfigSet`) and single config file parsing method (`load_config_file`).
* **Added** behavior tree entry point implementation (`Tree`).