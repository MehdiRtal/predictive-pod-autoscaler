## Usage

[Helm](https://helm.sh) must be installed to use the charts.  Please refer to
Helm's [documentation](https://helm.sh/docs) to get started.

Once Helm has been set up correctly, add the repo as follows:

    helm repo add ppa https://cloudstack0.github.io/predictive-pod-autoscaler

If you had already added this repo earlier, run `helm repo update` to retrieve
the latest versions of the packages.  You can then run `helm search repo ppa` to see the charts.

To install the predictive-pod-autoscaler chart:

    helm install my-predictive-pod-autoscaler ppa/predictive-pod-autoscaler

To uninstall the chart:

    helm uninstall my-predictive-pod-autoscaler
