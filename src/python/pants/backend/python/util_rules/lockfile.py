# Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""
Helpers for tools to generate their lockfiles
TODO:
- TODO: helpful error messages on Tools missing required fields
"""

from __future__ import annotations

from typing import Iterable, Type

from pants.backend.python.goals import lockfile
from pants.backend.python.goals.lockfile import GeneratePythonLockfile
from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.core.goals.generate_lockfiles import GenerateToolLockfileSentinel
from pants.engine.rules import rule
from pants.engine.unions import UnionRule
from pants.util.memo import memoized


class LockfileType:
    """The type of lockfile generation strategy to use for a tool."""

    @staticmethod
    def custom(cls) -> Iterable:
        """The plugin author defines its own export machinery."""
        yield from lockfile.rules()

    @staticmethod
    def pex_simple(cls) -> Iterable:
        """The tool can be just pip-installed."""

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
