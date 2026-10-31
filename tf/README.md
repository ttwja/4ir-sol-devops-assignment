# Install an AKS cluster with Terraform

## setup Terraform with az cli
You need to run a few az cli commands to setup a Terraform connection with az.

The Terraform will use a "service principle"(headless account) instead of you to create the AKS cluster
```
export ARM_SUBSCRIPTION_ID=YOUR_SUBSCRIPTION_ID
# az login
az ad sp create-for-rbac --name "terraform-automation" --role Contributor --scopes /subscriptions/$ARM_SUBSCRIPTION_ID
```
Keep the output of the above command and export a few environment variables
```
ARM_CLIENT_ID="appId"
ARM_CLIENT_SECERT="password"
ARM_TENANT_ID="tenant"
export ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENENT_ID ARM_SUBSCRIPTION_ID
```


Create the resource group, and a storage account, a storage container to store the "tfstate" file.

We should use a *shared* "tfstate" file between team members.
```
STORAGE_ACCOUNT_NAME=tfstate0ir40pulumi

az group create --name rg-terraform-state --location eastus

az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group rg-terraform-state --sku Standard_LRS --encryption-services blob

az storage container create --name tfstate --account-name $STORAGE_ACCOUNT_NAME
```

## Install AKS
Now you can run Terraform to install AKS
```
terraform apply
```
Once created, you can export kubeconfig and use it
```
terraform output kube_config|sed -e'1d' -e '$d' > azkube
export KUBECONFIG=./azkube
kubectl config get-contexts
```
![kubectl contexts](../img/kubectl_context.jpg)