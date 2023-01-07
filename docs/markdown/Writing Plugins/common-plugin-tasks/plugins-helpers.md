---
title: "Plugin helpers"
slug: "plugins-helpers"
excerpt: "Helpers which make writing plugins easier."
hidden: false
createdAt: "2023-01-07T22:23:00.000Z"
---
Pants has helpers to make writing plugins easier.

# Python

## Lockfiles

The lockfiles for most Python tools fit into common categories. Pants has helpers to generate the rules for lockfile generation.

- A single Python package that could be installed with `pip install my_tool`

```python
from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.engine.rules import collect_rules
from pants.backend.python.util_rules.lockfile import LockfileRules  # Lockfile helpers come from here

class Isort(PythonToolBase):
    options_scope = "isort"
    ...

def rules():
    return (
        *collect_rules(),
        *LockfileRules.from_tool(Isort),
    )
```

- A Python package which needs to know the Python interpreter constraints, like Bandit

```python
from dataclasses import dataclass

from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import InterpreterConstraintsField, PythonSourceField
from pants.backend.python.util_rules.lockfile import LockfileRules  # Lockfile helpers come from here
from pants.engine.rules import collect_rules
from pants.engine.target import FieldSet

@dataclass(frozen=True)
class BanditFieldSet(FieldSet):  # The FieldSet is necessary to get information about the sources, in this case the InterpreterConstraintsField
    required_fields = (PythonSourceField,)

    source: PythonSourceField
    interpreter_constraints: InterpreterConstraintsField

    ...

class Bandit(PythonToolBase):
    ...

def rules():
    return (
        *collect_rules(),
        *LockfileRules.from_tool_with_constraints(Bandit, BanditFieldSet),  # Pass the Tool and the FieldSet here 
    )
```

- A Python tool which includes first-party plugins, like Flake8

```python
from dataclasses import dataclass

from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import (
    InterpreterConstraintsField,
    PythonSourceField,
)
from pants.backend.python.util_rules.lockfile import LockfileRules
from pants.engine.rules import collect_rules
from pants.engine.target import FieldSet
from pants.util.ordered_set import FrozenOrderedSet

@dataclass(frozen=True)
class Flake8FieldSet(FieldSet):
    required_fields = (PythonSourceField,)

    source: PythonSourceField
    interpreter_constraints: InterpreterConstraintsField

    ...

class Flake8(PythonToolBase):
    options_scope = "flake8"

    ...

@dataclass(frozen=True)
class Flake8FirstPartyPlugins:
    requirement_strings: FrozenOrderedSet[str]
    interpreter_constraints_fields: FrozenOrderedSet[InterpreterConstraintsField]
    ...


def rules():
    return (
        *collect_rules(),
        *LockfileRules.from_tool_with_first_party_plugins(
            Flake8, Flake8FieldSet, Flake8FirstPartyPlugins
        ),
        ...
    )
```