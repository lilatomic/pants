# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from pants.backend.terraform.partition import partition_files_by_directory
from pants.backend.terraform.target_types import (
    TerraformBackendConfigField,
    TerraformDependenciesField,
)
from pants.backend.terraform.tool import TerraformProcess
from pants.backend.terraform.utils import terraform_arg, terraform_relpath
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.internals.native_engine import EMPTY_DIGEST, Digest, MergeDigests
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import DependenciesRequest, SourcesField, Targets


@dataclass(frozen=True)
class GetTerraformDependenciesRequest:
    source_files: SourceFiles
    directories: Tuple[str, ...]
    backend_config: SourceFiles
    dependencies_files: SourceFiles

    # Not initialising the backend means we won't access remote state. Useful for `validate`
    initialise_backend: bool = False


@dataclass(frozen=True)
class TerraformDependencies:
    fetched_deps: Tuple[Tuple[str, Digest], ...]


@rule
async def get_terraform_providers(
    req: GetTerraformDependenciesRequest,
) -> TerraformDependencies:
    args = ["init"]
    if req.backend_config.files:
        args.append(
            terraform_arg(
                "-backend-config",
                terraform_relpath(req.directories[0], req.backend_config.files[0]),
            )
        )
        backend_digest = req.backend_config.snapshot.digest
    else:
        backend_digest = EMPTY_DIGEST

    args.append(terraform_arg("-backend", str(req.initialise_backend)))

    with_backend_config = await Get(
        Digest,
        MergeDigests(
            [
                req.source_files.snapshot.digest,
                backend_digest,
                req.dependencies_files.snapshot.digest,
            ]
        ),
    )

    # TODO: Does this need to be a MultiGet? I think we will now always get one directory
    fetched_deps = await MultiGet(
        Get(
            FallibleProcessResult,
            TerraformProcess(
                args=tuple(args),
                input_digest=with_backend_config,
                output_files=(".terraform.lock.hcl",),
                output_directories=(".terraform",),
                description="Run `terraform init` to fetch dependencies",
                chdir=directory,
            ),
        )
        for directory in req.directories
    )

    return TerraformDependencies(
        tuple(zip(req.directories, (x.output_digest for x in fetched_deps)))
    )


@dataclass(frozen=True)
class TerraformInitRequest:
    sources: Iterable[SourcesField]
    backend_config: TerraformBackendConfigField
    dependencies: TerraformDependenciesField

    # Not initialising the backend means we won't access remote state. Useful for `validate`
    initialise_backend: bool = False


@dataclass(frozen=True)
class InitialisedTerraform:
    sources_and_deps: Digest
    terraform_files: tuple[str, ...]
    chdir: str


@rule
async def init_terraform(request: TerraformInitRequest) -> InitialisedTerraform:
    root_dependencies = await Get(Targets, DependenciesRequest(request.dependencies))

    source_files, backend_config, dependencies_files = await MultiGet(
        Get(SourceFiles, SourceFilesRequest(request.sources)),
        Get(SourceFiles, SourceFilesRequest([request.backend_config])),
        Get(SourceFiles, SourceFilesRequest([tgt.get(SourcesField) for tgt in root_dependencies])),
    )
    files_by_directory = partition_files_by_directory(source_files.files)

    fetched_deps = await Get(
        TerraformDependencies,
        GetTerraformDependenciesRequest(
            source_files,
            tuple(files_by_directory.keys()),
            backend_config,
            dependencies_files,
            initialise_backend=request.initialise_backend,
        ),
    )

    merged_fetched_deps = await Get(Digest, MergeDigests([x[1] for x in fetched_deps.fetched_deps]))

    sources_and_deps = await Get(
        Digest,
        MergeDigests(
            [source_files.snapshot.digest, merged_fetched_deps, dependencies_files.snapshot.digest]
        ),
    )

    assert len(files_by_directory) == 1, "Multiple directories found, unable to identify a root"
    chdir, files = next(iter(files_by_directory.items()))
    return InitialisedTerraform(sources_and_deps, tuple(files), chdir)


def rules():
    return collect_rules()
