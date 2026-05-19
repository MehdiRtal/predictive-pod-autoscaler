# Usage Guide

Once PPA is installed, you can enable proactive scaling for your applications by defining a `Model` resource and configuring KEDA to utilize it.

## 1. Define a Predictive Model
The `Model` Custom Resource triggers the automated pipeline that fetches historical metrics and trains a Prophet model for your workload.

```yaml
apiVersion: ppa.io/v1alpha1
kind: Model
metadata:
  name: my-app-cpu-prediction
  namespace: my-apps
spec:
  prometheusUrl: "http://prometheus-operated.monitoring:9090"
  queryType: "cpu" # Options: "cpu" | "memory"
  workload:
    type: "deployment"
    name: "my-app"
```

### Automation Workflow
When you apply this resource, the following sequence occurs automatically:
1.  **Orchestration**: Kro detects the new `Model`.
2.  **Initial Training**: An Argo Workflow trains the baseline model.
3.  **Scheduled Training**: A `CronWorkflow` ensures the model is retrained hourly.
4.  **Inference Service**: A KServe `InferenceService` is deployed to serve the latest model.

## 2. Configure KEDA ScaledObject
Link your workload to the PPA External Scaler by configuring KEDA to trigger based on the model's predictions.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app-scaler
  namespace: my-apps
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: external-push
      metadata:
        scalerAddress: ppa-scaler.ppa:9090
        modelName: my-app-cpu-prediction
        horizon: "5"       # Minutes to look ahead
        targetValue: "0.8"  # Target utilization (e.g., 80%)
```

## 3. Monitoring
Verify the lifecycle of your predictive models through the command line:

```bash
# Check training workflow status
argo list -n my-apps

# Check model availability and inference URL
kubectl get models my-app-cpu-prediction -o yaml
```
