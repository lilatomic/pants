# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pants.backend.terraform.target_types import TerraformModuleSourcesField, TerraformModuleTarget
from pants.backend.terraform.tool import TerraformProcess
from pants.core.goals.generate_lockfiles import (
    GenerateLockfile,
    GenerateLockfileResult,
    RequestedUserResolveNames,
    UserGenerateLockfiles,
)
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.internals.selectors import Get
from pants.engine.process import ProcessResult
from pants.engine.rules import Rule, collect_rules, rule
from pants.engine.unions import UnionRule


@dataclass(frozen=True)
class GenerateTerraformLockfile(GenerateLockfile):
    pass


class RequestedTerraformResolveNames(RequestedUserResolveNames):
    pass


@rule
async def setup_user_lockfile_requests(
    requested: RequestedTerraformResolveNames,
) -> UserGenerateLockfiles:
    return UserGenerateLockfiles()


@rule
async def generate_lockfile_from_sources(
    request: GenerateTerraformLockfile,
    target: TerraformModuleTarget,
) -> GenerateLockfileResult:
    source_files = await Get(
        SourceFiles, SourceFilesRequest([target.get(TerraformModuleSourcesField)])
    )

    result = await Get(
        ProcessResult,
        TerraformProcess(
            args=(
                "providers",
                "lock",
            ),
            input_digest=source_files.snapshot.digest,
            output_files=(".terraform.lock.hcl",),
            description=f"Update terraform lockfile for {request.resolve_name}",
            chdir="src/tf",
        ),
    )

    return GenerateLockfileResult(result.output_digest, request.resolve_name, request.lockfile_dest)


def rules() -> Iterable[Rule | UnionRule]:
    return (
        *collect_rules(),
        UnionRule(GenerateLockfile, GenerateTerraformLockfile),
        UnionRule(RequestedUserResolveNames, RequestedTerraformResolveNames),
    )
