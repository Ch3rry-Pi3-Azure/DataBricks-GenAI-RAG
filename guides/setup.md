# Project Setup Guide

This project provisions Azure OpenAI, Azure Storage, Azure Key Vault, and Azure Databricks resources using Terraform and includes helper scripts.

## Prerequisites
- Azure CLI (az) installed and authenticated
- Terraform installed (>= 1.5)
- Python (for running the helper scripts)

## Terraform Setup
Check if Terraform is installed and on PATH:

```powershell
terraform version
```

If you need to install or update Terraform on Windows, use one of these:

```powershell
winget install HashiCorp.Terraform
```

```powershell
choco install terraform -y
```

After installing, re-open PowerShell and re-run terraform version.

## Azure CLI
Check your Azure CLI and login status:

```powershell
az --version
az login
az account show
```

## Project Structure
- terraform/01_resource_group: Azure resource group
- terraform/02_azure_openai: Azure OpenAI account
- terraform/03_openai_deployment: Azure OpenAI model deployment
- terraform/04_databricks_workspace: Azure Databricks workspace
- terraform/05_key_vault: Azure Key Vault for secrets
- terraform/06_databricks_compute: Databricks cluster + Key Vault-backed secret scope
- terraform/07_notebooks: Databricks workspace notebooks
- terraform/08_serving_endpoint: Databricks model serving endpoint
- terraform/09_storage: Storage account + container (HNS enabled)
- terraform/10_access_connector: Databricks access connector (managed identity) + storage RBAC
- terraform/11_unity_catalog: Unity Catalog metastore, assignment, storage credential, external location
- scripts/: Helper scripts to deploy/destroy Terraform resources
- notebooks/: Placeholder for Databricks notebooks

## Configure Terraform
The deploy script writes terraform.tfvars files automatically.
If you want different defaults, edit DEFAULTS in scripts/deploy.py before running.
The deploy script also writes .env with OpenAI and Databricks outputs.

## Deploy Resources
From the repo root or scripts folder, run:

```powershell
python scripts\deploy.py
```

Optional flags:

```powershell
python scripts\deploy.py --rg-only
python scripts\deploy.py --openai-only
python scripts\deploy.py --deployment-only
python scripts\deploy.py --databricks-only
python scripts\deploy.py --keyvault-only
python scripts\deploy.py --storage-only
python scripts\deploy.py --access-connector-only
python scripts\deploy.py --uc-only
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --serving-only
```

## Register Model and Serve
1) Open `notebooks/RAG.ipynb` in Databricks and run the model registration cell.
   This registers the model in the workspace registry as `rag_model`.

2) Sync secrets to Key Vault (if `DATABRICKS_TOKEN` is not set, deploy.py will auto-create a PAT for serving):
```powershell
python scripts\deploy.py --keyvault-only
```

3) Deploy the serving endpoint:
```powershell
python scripts\deploy.py --serving-only
```

4) Query the endpoint (example payload):
```json
{
  "dataframe_split": {
    "columns": ["user_query"],
    "data": [["hello how are you?"]]
  }
}
```

## Destroy Resources
To tear down resources:

```powershell
python scripts\destroy.py
```

Optional flags:

```powershell
python scripts\destroy.py --rg-only
python scripts\destroy.py --openai-only
python scripts\destroy.py --deployment-only
python scripts\destroy.py --databricks-only
python scripts\destroy.py --keyvault-only
python scripts\destroy.py --storage-only
python scripts\destroy.py --access-connector-only
python scripts\destroy.py --uc-only
python scripts\destroy.py --compute-only
python scripts\destroy.py --notebooks-only
python scripts\destroy.py --serving-only
```

## Notes
- Azure OpenAI account names must be globally unique and alphanumeric.
- Azure OpenAI deployment names must be unique within the account.
- Databricks workspace names must be 3-30 characters and use letters, numbers, or hyphens.
- The deploy script stores Azure OpenAI secrets in Key Vault and creates a Databricks secret scope (default: aoai-scope).
- The access connector uses a managed identity and storage RBAC to avoid storage secrets in Key Vault.
- In notebooks, read secrets with dbutils.secrets.get("aoai-scope", "openai-api-base"), openai-api-key, openai-api-version, and openai-deployment-name.
- The deploy script grants Key Vault access to the Azure Databricks service principal (app id 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d).
- The Databricks compute stack installs the OpenAI SDK and Databricks Vector Search via cluster libraries.
- The deploy script uploads data/diabetes_treatment_faq.csv to the storage container after the storage stack applies.
- The Unity Catalog stack requires your Databricks account ID (set in scripts/deploy.py DEFAULTS or in terraform/11_unity_catalog/terraform.tfvars).
- If you run Terraform directly in terraform/11_unity_catalog, provide workspace_id in terraform.tfvars (the deploy script looks it up automatically).
- If your account already has a metastore in the workspace region, set existing_metastore_id to reuse it instead of creating a new one.
- The compute stack selects a non-ML LTS runtime and a compatible node type unless you override spark_version and node_type_id. use_ml_runtime remains enabled by default.
- Create the serving endpoint only after registering a model version in MLflow/Unity Catalog.
- If Terraform reports an unsupported Databricks resource, run `terraform init -upgrade` in that stack to pull a newer provider.
- The serving endpoint deploy resolves the latest registered model version automatically using the Databricks MLflow API.
- The serving endpoint injects Databricks + Azure OpenAI env vars via the Key Vault-backed secret scope (DATABRICKS_HOST/TOKEN and AZURE_OPENAI_ENDPOINT/API_KEY/API_VERSION).
- If `DATABRICKS_TOKEN` is not set, the deploy script will try to create a workspace PAT and store it in Key Vault. Set `AUTO_CREATE_DATABRICKS_PAT=0` to disable.
- The notebook uses the workspace MLflow registry (`mlflow.set_registry_uri("databricks")`). Switch this if you plan to use Unity Catalog.
- Names are built from prefixes plus a random pet name by default. Override variables if needed.
- The .env and terraform.tfvars files are gitignored.
