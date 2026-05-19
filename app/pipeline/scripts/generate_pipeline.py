import argparse

import yaml
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


def escape_helm(text: str) -> str:
    return text.replace("{{", "{{ `{{").replace("}}", "}}` }}")


class Config:
    def __init__(self, use_helm: bool = False):
        self.use_helm = use_helm

    @property
    def pipeline_image(self) -> str:
        if self.use_helm:
            return "{{ .Values.pipeline.image.repository }}:{{ .Values.pipeline.image.tag | default .Chart.AppVersion }}"
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
            Parameter(name="workload_type"),
            Parameter(name="workload_name"),
            Parameter(name="query_type"),
            Parameter(name="model_name"),
        ],
        artifact_repository_ref=ArtifactRepositoryRef(
            config_map=config.artifact_repo_configmap
        ),
    ) as cwt:
        fetch_data_template = Script(
            name="fetch-data",
            image=config.pipeline_image,
            source=_v("{{inputs.parameters}}"),
            args=["-m", "hera.workflows.runner", "-e", "src.pipeline:fetch_data"],
            command=["python"],
            outputs=[
                Artifact(
                    name="data", path="/tmp/data.csv", archive=NoneArchiveStrategy()
                )
            ],
            inputs=[
                Parameter(name="prometheus_url"),
                Parameter(name="workload_type"),
                Parameter(name="workload_name"),
                Parameter(name="workload_namespace"),
                Parameter(name="query_type"),
            ],
        )
        train_model_template = Script(
            name="train-model",
            image=config.pipeline_image,
            source=_v("{{inputs.parameters}}"),
            args=["-m", "hera.workflows.runner", "-e", "src.pipeline:train_model"],
            command=["python"],
            inputs=[Artifact(name="data", path="/tmp/data.csv")],
            outputs=[
                S3Artifact(
                    name="model",
                    path="/tmp/model.json",
                    archive=NoneArchiveStrategy(),
                    key=_v("models/{{workflow.name}}/model.json"),
                )
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
                        "name": _v("{{inputs.parameters.model_name}}"),
                        "namespace": _v("{{workflow.namespace}}"),
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
                                    "path": _v("{{inputs.parameters.model_s3_path}}"),
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
                        value=_v("{{workflow.parameters.prometheus_url}}"),
                    ),
                    Parameter(
                        name="workload_type",
                        value=_v("{{workflow.parameters.workload_type}}"),
                    ),
                    Parameter(
                        name="workload_name",
                        value=_v("{{workflow.parameters.workload_name}}"),
                    ),
                    Parameter(
                        name="workload_namespace", value=_v("{{workflow.namespace}}")
                    ),
                    Parameter(
                        name="query_type",
                        value=_v("{{workflow.parameters.query_type}}"),
                    ),
                ],
            )
            Step(
                name="train-model",
                template=train_model_template.name,
                arguments=[
                    Artifact(
                        name="data",
                        from_=_v("{{steps.fetch-data.outputs.artifacts.data}}"),
                    ),
                ],
            )
            Step(
                name="deploy-model",
                template=deploy_template.name,
                arguments=[
                    Parameter(
                        name="model_s3_path",
                        value=_v("models/{{workflow.name}}/model.json"),
                    ),
                    Parameter(
                        name="model_name",
                        value=_v("{{workflow.parameters.model_name}}"),
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
