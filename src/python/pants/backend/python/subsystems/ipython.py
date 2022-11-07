# Copyright 2020 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from pants.backend.python.subsystems.python_tool_base import PythonToolBase
from pants.backend.python.target_types import ConsoleScript, InterpreterConstraintsField
from pants.backend.python.util_rules.lockfile import LockfileType
from pants.engine.rules import collect_rules
from pants.engine.target import FieldSet
from pants.option.option_types import BoolOption
from pants.util.docutil import git_url
from pants.util.strutil import softwrap


class IPython(PythonToolBase):
    options_scope = "ipython"
    help = "The IPython enhanced REPL (https://ipython.org/)."

    default_version = "ipython>=7.34,<8"  # ipython 8 does not support Python 3.7.
    default_main = ConsoleScript("ipython")

    register_lockfile = True
    default_lockfile_resource = ("pants.backend.python.subsystems", "ipython.lock")
    default_lockfile_path = "src/python/pants/backend/python/subsystems/ipython.lock"
    default_lockfile_url = git_url(default_lockfile_path)

    ignore_cwd = BoolOption(
        advanced=True,
        default=True,
        help=softwrap(
            """
            Whether to tell IPython not to put the CWD on the import path.

            Normally you want this to be True, so that imports come from the hermetic
            environment Pants creates.

            However IPython<7.13.0 doesn't support this option, so if you're using an earlier
            version (e.g., because you have Python 2.7 code) then you will need to set this to False,
            and you may have issues with imports from your CWD shading the hermetic environment.
            """
        ),
    )


class _IpythonFieldSetForLockfiles(FieldSet):
    required_fields = (InterpreterConstraintsField,)


def rules():
    return (
        *collect_rules(),
        *LockfileType.python_with_constraints(IPython, _IpythonFieldSetForLockfiles),
    )
