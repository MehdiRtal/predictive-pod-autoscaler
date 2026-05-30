

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| https://kedacore.github.io/charts | keda | 2.19.0 |
| https://seaweedfs.github.io/seaweedfs/helm | seaweedfs | 4.28.0 |
| oci://ghcr.io/argoproj/argo-helm | argo-workflows | 1.0.14 |
| oci://ghcr.io/kserve/charts | kserve-crd | v0.18.0-rc1 |
| oci://ghcr.io/kserve/charts | kserve-resources | v0.18.0-rc1 |
| oci://registry.k8s.io/kro/charts | kro | 0.9.1 |

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| argo-workflows.enabled | bool | `false` |  |
| keda.enabled | bool | `false` |  |
| kro.enabled | bool | `false` |  |
| kserve.enabled | bool | `false` |  |
| kserve.kserve.certManager.enabled | bool | `false` |  |
| pipeline.image.pullPolicy | string | `"IfNotPresent"` |  |
| pipeline.image.repository | string | `"ghcr.io/mehdirtal/predictive-pod-autoscaler/pipeline"` |  |
| pipeline.image.tag | string | `"0.2.0"` |  |
| runtime.image.pullPolicy | string | `"IfNotPresent"` |  |
| runtime.image.repository | string | `"ghcr.io/mehdirtal/predictive-pod-autoscaler/runtime"` |  |
| runtime.image.tag | string | `"0.1.0"` |  |
| runtime.resources.limits.cpu | string | `"1"` |  |
| runtime.resources.limits.memory | string | `"2Gi"` |  |
| runtime.resources.requests.cpu | string | `"1"` |  |
| runtime.resources.requests.memory | string | `"2Gi"` |  |
| s3.create | bool | `true` |  |
| s3.externalConfig.accessKey | string | `""` |  |
| s3.externalConfig.bucket | string | `""` |  |
| s3.externalConfig.endpoint | string | `""` |  |
| s3.externalConfig.insecure | bool | `false` |  |
| s3.externalConfig.secretKey | string | `""` |  |
| scaler.enabled | bool | `true` |  |
| scaler.image.pullPolicy | string | `"IfNotPresent"` |  |
| scaler.image.repository | string | `"ghcr.io/mehdirtal/predictive-pod-autoscaler/scaler"` |  |
| scaler.image.tag | string | `"0.2.0"` |  |
| scaler.replicas | int | `1` |  |
| scaler.resources.limits.cpu | string | `"0.5"` |  |
| scaler.resources.limits.memory | string | `"512Mi"` |  |
| scaler.resources.requests.cpu | string | `"0.25"` |  |
| scaler.resources.requests.memory | string | `"256Mi"` |  |
| scaler.securityContext.allowPrivilegeEscalation | bool | `false` |  |
| scaler.securityContext.capabilities.drop[0] | string | `"ALL"` |  |
| scaler.securityContext.runAsGroup | int | `1000` |  |
| scaler.securityContext.runAsNonRoot | bool | `true` |  |
| scaler.securityContext.runAsUser | int | `1000` |  |
| scaler.securityContext.seccompProfile.type | string | `"RuntimeDefault"` |  |
| scaler.service.port | int | `9090` |  |
| scaler.service.type | string | `"ClusterIP"` |  |
| seaweedfs.allInOne.data.size | string | `"10Gi"` |  |
| seaweedfs.allInOne.data.type | string | `"persistentVolumeClaim"` |  |
| seaweedfs.allInOne.enabled | bool | `true` |  |
| seaweedfs.allInOne.s3.createBuckets[0].name | string | `"ppa"` |  |
| seaweedfs.allInOne.s3.enabled | bool | `true` |  |
| seaweedfs.filer.enabled | bool | `false` |  |
| seaweedfs.master.enabled | bool | `false` |  |
| seaweedfs.s3.credentials.admin.accessKey | string | `"admin"` |  |
| seaweedfs.s3.credentials.admin.secretKey | string | `"admin123"` |  |
| seaweedfs.s3.enableAuth | bool | `true` |  |
| seaweedfs.volume.enabled | bool | `false` |  |
