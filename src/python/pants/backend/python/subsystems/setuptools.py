# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from dataclasses import dataclass

from pants.backend.python.subsystems.python_tool_base import PythonToolRequirementsBase
from pants.backend.python.target_types import PythonProvidesField
from pants.backend.python.util_rules.lockfile import LockfileRules
from pants.core.goals.package import PackageFieldSet
from pants.util.docutil import git_url


@dataclass(frozen=True)
class PythonDistributionFieldSet(PackageFieldSet):
    required_fields = (PythonProvidesField,)

    provides: PythonProvidesField


class Setuptools(PythonToolRequirementsBase):
    options_scope = "setuptools"
    help = "Python setuptools, used to package `python_distribution` targets."

    default_version = "setuptools>=63.1.0,<64.0"
    default_extra_requirements = ["wheel>=0.35.1,<0.38"]

    register_lockfile = True
    default_lockfile_resource = ("pants.backend.python.subsystems", "setuptools.lock")
    default_lockfile_path = "src/python/pants/backend/python/subsystems/setuptools.lock"
    default_lockfile_url = git_url(default_lockfile_path)


def rules():
    return (
        *Setuptools.rules(),
        *LockfileRules.from_tool_with_constraints(Setuptools, PythonDistributionFieldSet),
    )
