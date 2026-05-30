import argparse

import yaml
from hera.expr import g
from hera.workflows import (
    Artifact,
    ClusterWorkflowTemplate,
    NoneArchiveStrategy,
    Parameter,
    Resource,
    S3Artifact,
    Script,
    Step,
    Steps,
)
from hera.workflows.models import ArtifactRepositoryRef
from hera.workflows.script import RunnerScriptConstructor

from src.pipeline import fetch_data, train_model


class HelmRunnerScriptConstructor(RunnerScriptConstructor):
    def __init__(self):
        super().__init__()

    def generate_source(self, instance: Script) -> str:
        return escape_helm(super().generate_source(instance))


def escape_helm(text: str) -> str:
    return text.replace("{{", "{{ `{{").replace("}}", "}}` }}")


class Config:
    def __init__(self, use_helm: bool = False):
        self.use_helm = use_helm

    @property
    def constructor(self) -> HelmRunnerScriptConstructor | RunnerScriptConstructor:
        return (
            HelmRunnerScriptConstructor()
            if self.use_helm
            else RunnerScriptConstructor()
        )

    @property
    def pipeline_image(self) -> str:
        if self.use_helm:
            return "{{ .Values.pipeline.image.repository }}:{{ .Values.pipeline.image.tag }}"
        return "ghcr.io/mehdirtal/pipeline:latest"

    @property
    def storage_config_name(self) -> str:
        if self.use_helm:
            return '{{ include "ppa.fullname" . }}-storage-config'
        return "ppa-storage-config"

    @property
    def artifact_repo_configmap(self) -> str:
        if self.use_helm:
            return '{{ include "ppa.fullname" . }}-artifact-repository'
        return "ppa-artifact-repository"

    @property
    def pipeline_name(self) -> str:
        if self.use_helm:
            return '{{ include "ppa.fullname" . }}-pipeline'
        return "ppa-pipeline"

    @property
    def service_account_name(self) -> str:
        if self.use_helm:
            return '{{ include "ppa.fullname" . }}-pipeline'
        return "ppa-pipeline"


def generate_pipeline(config: Config) -> str:
    def _v(val: str) -> str:
        if config.use_helm:
            return escape_helm(val)
        return val

    with ClusterWorkflowTemplate(
        name=config.pipeline_name,
        entrypoint="main",
        service_account_name=config.service_account_name,
        arguments=[
            Parameter(name="prometheus_url"),
            Parameter(name="target_ref_api_version"),
            Parameter(name="target_ref_kind"),
            Parameter(name="target_ref_name"),
            Parameter(name="namespace"),
            Parameter(name="query_type"),
            Parameter(name="lookBackInterval"),
            Parameter(name="windowInterval"),
            Parameter(name="custom_query", default=""),
            Parameter(name="model_name"),
        ],
        artifact_repository_ref=ArtifactRepositoryRef(
            config_map=config.artifact_repo_configmap
        ),
    ) as cwt:
        fetch_data_template = Script(
            name="fetch-data",
            image=config.pipeline_image,
            constructor=config.constructor,
            source=fetch_data,
        )
        train_model_template = Script(
            name="train-model",
            image=config.pipeline_image,
            constructor=config.constructor,
            source=train_model,
            outputs=[
                S3Artifact(
                    name="model",
                    path="/tmp/hera-outputs/artifacts/model",
                    key=_v(f"models/{g.workflow.name:$}-{g.workflow.uid:$}/model.json"),
                    archive=NoneArchiveStrategy(),
                ),
            ],
        )
        deploy_template = Resource(
            name="deploy-model",
            inputs=[Parameter(name="model_s3_path"), Parameter(name="model_name")],
            action="apply",
            set_owner_reference=True,
            manifest=yaml.dump(
                {
                    "apiVersion": "serving.kserve.io/v1beta1",
                    "kind": "InferenceService",
                    "metadata": {
                        "name": _v(f"{g.inputs.parameters.model_name:$}"),
                        "namespace": _v(f"{g.workflow.namespace:$}"),
                        "annotations": {
                            "serving.kserve.io/secretName": config.storage_config_name
                        },
                    },
                    "spec": {
                        "predictor": {
                            "minReplicas": 0,
                            "maxReplicas": 1,
                            "model": {
                                "modelFormat": {"name": "prophet"},
                                "storage": {
                                    "key": "default",
                                    "path": _v(
                                        f"{g.inputs.parameters.model_s3_path:$}"
                                    ),
                                },
                                "protocolVersion": "v2",
                                "ports": [
                                    {
                                        "name": "h2c",
                                        "containerPort": 9000,
                                        "protocol": "TCP",
                                    }
                                ],
                            },
                        },
                    },
                }
            ),
        )
        with Steps(name="main"):
            Step(
                name="fetch-data",
                template=fetch_data_template.name,
                arguments=[
                    Parameter(
                        name="prometheus_url",
                        value=_v(f"{g.workflow.parameters.prometheus_url:$}"),
                    ),
                    Parameter(
                        name="target_ref_api_version",
                        value=_v(f"{g.workflow.parameters.target_ref_api_version:$}"),
                    ),
                    Parameter(
                        name="target_ref_kind",
                        value=_v(f"{g.workflow.parameters.target_ref_kind:$}"),
                    ),
                    Parameter(
                        name="target_ref_name",
                        value=_v(f"{g.workflow.parameters.target_ref_name:$}"),
                    ),
                    Parameter(
                        name="namespace",
                        value=_v(f"{g.workflow.namespace:$}"),
                    ),
                    Parameter(
                        name="query_type",
                        value=_v(f"{g.workflow.parameters.query_type:$}"),
                    ),
                    Parameter(
                        name="lookBackInterval",
                        value=_v(f"{g.workflow.parameters.lookBackInterval:$}"),
                    ),
                    Parameter(
                        name="windowInterval",
                        value=_v(f"{g.workflow.parameters.windowInterval:$}"),
                    ),
                    Parameter(
                        name="custom_query",
                        value=_v(f"{g.workflow.parameters.custom_query:$}"),
                    ),
                ],
            )
            Step(
                name="train-model",
                template=train_model_template.name,
                arguments=[
                    Artifact(
                        name="data",
                        from_=_v(
                            f"{g.steps.get('fetch-data').outputs.artifacts.data:$}"
                        ),
                    ),
                ],
            )
            Step(
                name="deploy-model",
                template=deploy_template.name,
                arguments=[
                    Parameter(
                        name="model_s3_path",
                        value=_v(
                            f"models/{g.workflow.name:$}-{g.workflow.uid:$}/model.json"
                        ),
                    ),
                    Parameter(
                        name="model_name",
                        value=_v(f"{g.workflow.parameters.model_name:$}"),
                    ),
                ],
            )

    res = cwt.to_yaml()
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--helm",
        action="store_true",
    )
    args = parser.parse_args()

    config = Config(use_helm=args.helm)
    pipeline_yaml = generate_pipeline(config)
    print(pipeline_yaml)
