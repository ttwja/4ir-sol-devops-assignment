#!/bin/bash

SUBSCRIPTION_ID=25a49170-e136-420a-98a5-d0c682684a07
# az ad sp create-for-rbac --name "terraform-automation" --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID
# az ad sp show --id 50c34f85-9b4b-4e0b-99e9-cd4a8edfa4de


STORAGE_ACCOUNT_NAME=tfstate0ir40pulumi

az group create --name rg-terraform-state --location eastus

az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group rg-terraform-state --sku Standard_LRS --encryption-services blob

az storage container create --name tfstate --account-name $STORAGE_ACCOUNT_NAME
