# Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""
Helpers for tools to generate their lockfiles
TODO:
- TODO: helpful error messages on Tools missing required fields
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Type

from pants.backend.python.goals import lockfile
from pants.backend.python.goals.lockfile import GeneratePythonLockfile
from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.core.goals.generate_lockfiles import GenerateToolLockfileSentinel
from pants.engine.rules import rule
from pants.engine.unions import UnionRule
from pants.util.memo import memoized


class LockfileType(Enum):
    """The type of lockfile generation strategy to use for a tool."""

    CUSTOM = "custom"
    """The plugin author defines its own export machinery"""

    PEX_SIMPLE = "pex_simple"
    """The tool can be just pip-installed"""

    def default_rules(self, cls) -> Iterable:
        """Return an iterable of rules defining the default lockfile generation logic for this
        `PartitionerType."""

        if self == LockfileType.CUSTOM:
            # All rules are custom defined, none are default
            return
        elif self == LockfileType.PEX_SIMPLE:
            rules_generator = _pex_simple_lockfile_rules(cls)
            yield from rules_generator
            yield from lockfile.rules()


@memoized
def _pex_simple_lockfile_rules(python_tool: Type[PythonToolBase]) -> Iterable:
    class SimplePexLockfileSentinel(GenerateToolLockfileSentinel):
        resolve_name = python_tool.options_scope

    @rule(_param_type_overrides={"request": SimplePexLockfileSentinel, "tool": python_tool})
    async def lockfile_generator(
        request: GenerateToolLockfileSentinel,
        tool: PythonToolBase,
    ) -> GeneratePythonLockfile:
        return GeneratePythonLockfile.from_tool(tool)

    return (UnionRule(GenerateToolLockfileSentinel, SimplePexLockfileSentinel), lockfile_generator)
