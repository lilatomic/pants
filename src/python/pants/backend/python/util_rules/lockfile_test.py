# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from textwrap import dedent
from typing import Iterable, Type

from pants.backend.python.dependency_inference.rules import import_rules
from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import ConsoleScript
from pants.backend.python.util_rules.lockfile import LockfileRules
from pants.core.goals import generate_lockfiles
from pants.core.goals.generate_lockfiles import GenerateLockfilesGoal, GenerateToolLockfileSentinel
from pants.engine.target import Dependencies, SingleSourceField, Target
from pants.engine.unions import UnionRule
from pants.testutil.rule_runner import RuleRunner


def _get_generated_lockfile_sentinel(
    rules: Iterable, subsystem: Type[PythonToolBase]
) -> Type[GenerateToolLockfileSentinel]:
    """Fish the generated lockfile sentinel out of the pool of rules so it can be used in a
    QueryRule."""
    return next(
        r
        for r in rules
        if isinstance(r, UnionRule)
        and r.union_base == GenerateToolLockfileSentinel
        and issubclass(r.union_member, GenerateToolLockfileSentinel)  # TypeGuard keeps mypy happy
        and r.union_member.resolve_name == subsystem.options_scope
    ).union_member


class FakeTool(PythonToolBase):
    options_scope = "cowsay"
    name = "Cowsay"
    help = "A tool to test pants"

    default_version = "cowsay==5.0"
    default_main = ConsoleScript("cowsay")

    register_interpreter_constraints = True
    default_interpreter_constraints = ["CPython>=3.7,<4"]

    register_lockfile = True
    default_lockfile_path = "cowsay.lock"
    default_lockfile_resource = ("", "")
    default_lockfile_url = " "


class MockSourceField(SingleSourceField):
    ...


class MockDependencies(Dependencies):
    ...


class MockTarget(Target):
    alias = "tgt"
    core_fields = (MockSourceField, MockDependencies)


def mk_rule_runner() -> RuleRunner:
    generated_rules = tuple(LockfileRules.from_tool(FakeTool))

    rule_runner = RuleRunner(
        rules=[
            *generate_lockfiles.rules(),
            *import_rules(),
            *generated_rules,
            *FakeTool.rules(),  # type: ignore[call-arg] # seems to only be a problem in this file
        ],
        target_types=[MockTarget],
    )

    rule_runner.write_files(
        {"project/example.ext": "", "project/BUILD": "tgt(source='example.ext')"}
    )
    return rule_runner


def test_simple_python_lockfile():
    """Test that the `LockfileType.PEX_SIMPLE` resolved the graph and generates the lockfile."""

    rule_runner = mk_rule_runner()

    result = rule_runner.run_goal_rule(
        GenerateLockfilesGoal,
        args=[
            "--resolve=cowsay",
            "--cowsay-lockfile=aaa.lock",
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    assert result
    lockfile_content = rule_runner.read_file("aaa.lock")
    assert (
        dedent(
            f"""\
        //   "generated_with_requirements": [
        //     "{FakeTool.default_version}"
        //   ],
    """
        )
        in lockfile_content
    )
