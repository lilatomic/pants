# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pants.backend.terraform.partition import partition_files_by_directory
from pants.backend.terraform.target_types import TerraformModuleSourcesField, TerraformModuleTarget
from pants.backend.terraform.tool import TerraformProcess
from pants.core.goals.generate_lockfiles import (
    GenerateLockfile,
    GenerateLockfileResult,
    KnownUserResolveNames,
    KnownUserResolveNamesRequest,
    RequestedUserResolveNames,
    UserGenerateLockfiles,
)
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Addresses
from pants.engine.internals.native_engine import Address
from pants.engine.internals.selectors import Get
from pants.engine.process import ProcessResult
from pants.engine.rules import Rule, collect_rules, rule
from pants.engine.target import AllTargets, Targets
from pants.engine.unions import UnionRule


@dataclass(frozen=True)
class GenerateTerraformLockfile(GenerateLockfile):
    target: TerraformModuleTarget


class KnownTerraformResolveNamesRequest(KnownUserResolveNamesRequest):
    pass


class RequestedTerraformResolveNames(RequestedUserResolveNames):
    pass


@rule
async def identify_user_resolves_from_terraform_files(
    _: KnownTerraformResolveNamesRequest,
    all_targets: AllTargets,
) -> KnownUserResolveNames:
    known_terraform_module_dirs = []
    for tgt in all_targets:
        if tgt.has_field(TerraformModuleSourcesField):
            known_terraform_module_dirs.append(tgt.residence_dir)

    return KnownUserResolveNames(
        names=tuple(known_terraform_module_dirs),
        option_name="[terraform].resolves",
        requested_resolve_names_cls=RequestedTerraformResolveNames,
    )


@rule
async def setup_user_lockfile_requests(
    requested: RequestedTerraformResolveNames,
) -> UserGenerateLockfiles:
    print(requested)

    [tgt] = await Get(Targets, Addresses([Address(requested[0])]))
    assert isinstance(tgt, TerraformModuleTarget)

    return UserGenerateLockfiles(
        [
            GenerateTerraformLockfile(
                target=tgt,
                resolve_name=requested[0],
                lockfile_dest=(Path(tgt.residence_dir) / ".terraform.lock.hcl").as_posix(),
                diff=False,
            )
        ]
    )


@rule
async def generate_lockfile_from_sources(
    request: GenerateTerraformLockfile,
) -> GenerateLockfileResult:
    source_files = await Get(
        SourceFiles, SourceFilesRequest([request.target.get(TerraformModuleSourcesField)])
    )
    files_by_directory = partition_files_by_directory(source_files.files)
    assert (
        len(files_by_directory) == 1
    ), "Asked to generate a lockfile for Terraform files in multiple directories, we can't determine where the root is"

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
            chdir=next(iter(files_by_directory.keys())),
        ),
    )

    return GenerateLockfileResult(result.output_digest, request.resolve_name, request.lockfile_dest)


def rules() -> Iterable[Rule | UnionRule]:
    return (
        *collect_rules(),
        UnionRule(GenerateLockfile, GenerateTerraformLockfile),
        UnionRule(KnownUserResolveNamesRequest, KnownTerraformResolveNamesRequest),
        UnionRule(RequestedUserResolveNames, RequestedTerraformResolveNames),
    )
