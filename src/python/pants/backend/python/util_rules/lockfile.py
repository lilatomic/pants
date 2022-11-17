# Copyright 2022 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

"""
Helpers for tools to generate their lockfiles
TODO:
- TODO: helpful error messages on Tools missing required fields
"""

from __future__ import annotations

from typing import Iterable, Type

from typing_extensions import Protocol

from pants.backend.python.goals import lockfile
from pants.backend.python.goals.lockfile import GeneratePythonLockfile
from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.target_types import InterpreterConstraintsField
from pants.backend.python.util_rules.partition import _find_all_unique_interpreter_constraints
from pants.core.goals.generate_lockfiles import GenerateToolLockfileSentinel
from pants.engine.rules import rule
from pants.engine.target import FieldSet
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel
from pants.util.memo import memoized
from pants.util.ordered_set import FrozenOrderedSet
from pants.util.strutil import softwrap


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

    @staticmethod
    def python_with_constraints(cls, field_set_type):
        """This tool needs to identify interpreter versions used in the project."""
        rules_generator = _pex_constraints_lockfile_rules(cls, field_set_type)
        yield from rules_generator
        yield from lockfile.rules()

    @staticmethod
    def python_with_first_party(cls, field_set_type, first_part_plugins_type):
        rules_generator = _pex_with_first_party_lockfile_rules(
            cls, field_set_type, first_part_plugins_type
        )
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


@memoized
def _pex_constraints_lockfile_rules(
    python_tool: Type[PythonToolBase], field_set_type: type[FieldSet]
) -> Iterable:
    class ConstraintsPexLockfileSentinel(GenerateToolLockfileSentinel):
        resolve_name = python_tool.options_scope

    @rule(
        _param_type_overrides={"request": ConstraintsPexLockfileSentinel, "tool": python_tool},
        desc=softwrap(
            f"""
            Determine all Python interpreter versions used by {getattr(python_tool, "name", python_tool.options_scope)} in your project
            (for lockfile generation)
            """
        ),
        level=LogLevel.DEBUG,
    )
    async def lockfile_generator(
        request: GenerateToolLockfileSentinel,
        tool: PythonToolBase,
        python_setup: PythonSetup,
    ) -> GeneratePythonLockfile:
        if not tool.uses_custom_lockfile:
            return GeneratePythonLockfile.from_tool(tool)

        constraints = await _find_all_unique_interpreter_constraints(
            python_setup,
            field_set_type,
        )
        return GeneratePythonLockfile.from_tool(
            tool,
            constraints,
        )

    return (
        UnionRule(GenerateToolLockfileSentinel, ConstraintsPexLockfileSentinel),
        lockfile_generator,
    )


class HasFirstPartyPlugins(Protocol):
    @property
    def interpreter_constraints_fields(self) -> FrozenOrderedSet[InterpreterConstraintsField]:
        ...

    @property
    def requirement_strings(self) -> FrozenOrderedSet[str]:
        ...


@memoized
def _pex_with_first_party_lockfile_rules(
    python_tool: Type[PythonToolBase],
    field_set_type: type[FieldSet],
    first_part_plugins_type: type[HasFirstPartyPlugins],
) -> Iterable:
    class PexAndFirstPartyLockfileSentinel(GenerateToolLockfileSentinel):
        resolve_name = python_tool.options_scope

    @rule(
        _param_type_overrides={
            "request": PexAndFirstPartyLockfileSentinel,
            "tool": python_tool,
            "first_party_plugins": first_part_plugins_type,
        },
        desc=softwrap(
            f"""
        Determine all Python interpreter versions used by {getattr(python_tool, "name", python_tool.options_scope)} in your project
        (for lockfile generation)
        """
        ),
        level=LogLevel.DEBUG,
    )
    async def lockfile_generator(
        request: GenerateToolLockfileSentinel,
        first_party_plugins: HasFirstPartyPlugins,
        tool: PythonToolBase,
        python_setup: PythonSetup,
    ) -> GeneratePythonLockfile:
        if not tool.uses_custom_lockfile:
            return GeneratePythonLockfile.from_tool(tool)

        constraints = await _find_all_unique_interpreter_constraints(
            python_setup,
            field_set_type,
            extra_constraints_per_tgt=first_party_plugins.interpreter_constraints_fields,
        )
        return GeneratePythonLockfile.from_tool(
            tool,
            constraints,
            extra_requirements=first_party_plugins.requirement_strings,
        )

    return (
        UnionRule(GenerateToolLockfileSentinel, PexAndFirstPartyLockfileSentinel),
        lockfile_generator,
    )
