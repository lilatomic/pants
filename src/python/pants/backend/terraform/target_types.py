# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

from dataclasses import dataclass

from pants.engine.rules import collect_rules, rule
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    AllTargets,
    Dependencies,
    DescriptionField,
    FieldSet,
    MultipleSourcesField,
    OptionalSingleSourceField,
    Target,
    Targets,
    generate_multiple_sources_field_help_message,
)
from pants.util.strutil import help_text


class TerraformDependenciesField(Dependencies):
    pass


class TerraformModuleSourcesField(MultipleSourcesField):
    default = ("*.tf",)
    expected_file_extensions = (".tf",)
    ban_subdirectories = True
    help = generate_multiple_sources_field_help_message(
        "Example: `sources=['example.tf', 'new_*.tf', '!old_ignore.tf']`"
    )


@dataclass(frozen=True)
class TerraformFieldSet(FieldSet):
    required_fields = (TerraformModuleSourcesField,)

    sources: TerraformModuleSourcesField


class TerraformModuleTarget(Target):
    alias = "terraform_module"
    core_fields = (*COMMON_TARGET_FIELDS, TerraformDependenciesField, TerraformModuleSourcesField)
    help = help_text(
        """
        A single Terraform module corresponding to a directory.

        There must only be one `terraform_module` in a directory.

        Use `terraform_modules` to generate `terraform_module` targets for less boilerplate.
        """
    )


class TerraformBackendConfigField(OptionalSingleSourceField):
    alias = "backend_config"
    help = "Configuration to be merged with what is in the configuration file's 'backend' block"

    def empty(self) -> TerraformBackendConfigField:
        """Clear the backend config to ensure that."""
        return TerraformBackendConfigField(None, self.address)


class TerraformVarFilesField(MultipleSourcesField):
    alias = "var_files"
    default = ("*.tfvars",)
    expected_file_extensions = (".tfvars",)
    help = generate_multiple_sources_field_help_message(
        "Example: `var_files=['common.tfvars', 'prod.tfvars']`"
    )


class TerraformDeploymentTarget(Target):
    alias = "terraform_deployment"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        TerraformDependenciesField,
        TerraformModuleSourcesField,
        TerraformBackendConfigField,
        TerraformVarFilesField,
    )
    help = "A deployment of Terraform"


@dataclass(frozen=True)
class TerraformDeploymentFieldSet(FieldSet):
    required_fields = (
        TerraformDependenciesField,
        TerraformModuleSourcesField,
    )
    description: DescriptionField
    sources: TerraformModuleSourcesField

    backend_config: TerraformBackendConfigField
    var_files: TerraformVarFilesField


class AllTerraformDeploymentTargets(Targets):
    pass


@rule
def all_terraform_deployment_targets(targets: AllTargets) -> AllTerraformDeploymentTargets:
    return AllTerraformDeploymentTargets(
        tgt for tgt in targets if TerraformDeploymentFieldSet.is_applicable(tgt)
    )


def rules():
    return collect_rules()
