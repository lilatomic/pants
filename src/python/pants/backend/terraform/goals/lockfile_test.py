# Copyright 2023 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).
import pytest

from pants.backend.terraform import dependency_inference, tool
from pants.backend.terraform.goals import lockfile
from pants.backend.terraform.goals.lockfile import GenerateTerraformLockfile
from pants.backend.terraform.target_types import TerraformModuleTarget
from pants.core.goals.generate_lockfiles import GenerateLockfileResult
from pants.core.util_rules import source_files
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import DigestContents
from pants.engine.internals.native_engine import Address
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *tool.rules(),
            *lockfile.rules(),
            *source_files.rules(),
            *dependency_inference.rules(),
            QueryRule(
                GenerateLockfileResult,
                (
                    GenerateTerraformLockfile,
                    TerraformModuleTarget,
                ),
            ),
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[TerraformModuleTarget],
    )
    rule_runner.set_options([], env_inherit={"PATH"})
    return rule_runner


def run_lockfiles(rule_runner: RuleRunner, target: TerraformModuleTarget) -> DigestContents:
    lockfile = rule_runner.request(
        GenerateLockfileResult,
        [
            GenerateTerraformLockfile(
                target=target,
                resolve_name="tf",
                lockfile_dest="src/tf/.terraform.lock.hcl",
                diff=False,
            ),
            target,
        ],
    )

    digest_contents = rule_runner.request(DigestContents, [lockfile.digest])
    return digest_contents


def test_lock_single_provider(rule_runner: RuleRunner):
    target_name = "tf0"
    rule_runner.write_files(
        {
            "src/tf/main.tf": 'resource "null_resource" "dep" {}',
            "src/tf/BUILD": f"terraform_module(name='{target_name}')",
        }
    )
    tgt = rule_runner.get_target(Address("src/tf", target_name=target_name))
    assert isinstance(tgt, TerraformModuleTarget)

    v = run_lockfiles(rule_runner, tgt)
    assert v
    assert any(b"registry.terraform.io/hashicorp/null" in x.content for x in v)
