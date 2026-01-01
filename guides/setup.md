# RAG Project Setup Guide

This project provisions Azure OpenAI, Azure Storage, Azure Key Vault, and Azure Databricks resources using Terraform and includes helper scripts for a RAG workflow (Unity Catalog + Vector Search + serving).

## Prerequisites
- Azure CLI (az) installed and authenticated
- Terraform installed (>= 1.5)
- Python 3.10+ (or use uv and prefix commands with `uv run`)

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
- data/: Seed CSV data used by the RAG notebook
- terraform/01_resource_group: Azure resource group
- terraform/02_azure_openai: Azure OpenAI account
- terraform/03_openai_deployment: Azure OpenAI model deployment
- terraform/04_databricks_workspace: Azure Databricks workspace
- terraform/05_key_vault: Azure Key Vault for secrets
- terraform/06_databricks_service_principal: Databricks service principal + entitlements
- terraform/07_storage: Storage account + container (HNS enabled)
- terraform/08_access_connector: Databricks access connector (managed identity) + storage RBAC
- terraform/09_unity_catalog: Unity Catalog metastore, assignment, storage credential, external location
- terraform/10_databricks_compute: Databricks cluster + Key Vault-backed secret scope
- terraform/11_notebooks: Databricks workspace notebooks
- terraform/12_serving_endpoint: Databricks model serving endpoint
- terraform/13_vector_search_permissions: Vector Search endpoint permissions for the SP
- terraform/14_uc_grants: Unity Catalog grants for the SP
- scripts/: Helper scripts to deploy/destroy Terraform resources
- notebooks/: Databricks notebooks

## Configure Terraform
The deploy script writes terraform.tfvars files automatically.
If you want different defaults, edit DEFAULTS in scripts/deploy.py before running.
The deploy script also writes .env with OpenAI and Databricks outputs.
Service principal OAuth for serving:
- Export `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, and `DATABRICKS_TENANT_ID`.
- Run `python scripts\deploy.py --sp-only` to add the SP to the workspace.
- Run `python scripts\deploy.py --keyvault-only` to sync the SP secrets into Key Vault.
`--sp-only` creates the SP at both the account and workspace level so Unity Catalog can grant permissions.

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
python scripts\deploy.py --sp-only
python scripts\deploy.py --storage-only
python scripts\deploy.py --access-connector-only
python scripts\deploy.py --uc-only
python scripts\deploy.py --sp-bootstrap
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --serving-only
python scripts\deploy.py --vector-perms-only
python scripts\deploy.py --uc-grants-only
```

## Data + Unity Catalog
- The storage stack uploads `data/diabetes_treatment_faq.csv` into the container.
- The UC stack creates the storage credential + external location.
- The RAG notebook creates an external volume and reads the CSV from `/Volumes/<catalog>/<schema>/<volume>/...`.

## Register Model and Serve
1) Open `notebooks/RAG.ipynb` in Databricks and run the flow to:
   - create the Delta table,
   - build the Vector Search index,
   - log and register `rag_model`.

2) Export Databricks SP credentials and sync secrets to Key Vault:
```powershell
$env:DATABRICKS_CLIENT_ID = "<app-id>"
$env:DATABRICKS_CLIENT_SECRET = "<client-secret>"
$env:DATABRICKS_TENANT_ID = "<tenant-id>"
python scripts\deploy.py --sp-only
python scripts\deploy.py --keyvault-only
```

If you want this automated (create/rotate the SP secret + sync Key Vault):
```powershell
python scripts\deploy.py --sp-bootstrap
```
This uses Azure CLI to create or rotate the SP secret and writes the values into `.env`.

3) Deploy the serving endpoint:
```powershell
python scripts\deploy.py --serving-only
```

4) Query the endpoint (example payload):
```json
{
  "dataframe_records": [
    { "query": "what is diabetes?" }
  ]
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
python scripts\destroy.py --sp-only
python scripts\destroy.py --compute-only
python scripts\destroy.py --notebooks-only
python scripts\destroy.py --serving-only
python scripts\destroy.py --vector-perms-only
python scripts\destroy.py --uc-grants-only
```

## Notes
- Azure OpenAI account names must be globally unique and alphanumeric.
- Azure OpenAI deployment names must be unique within the account.
- Databricks workspace names must be 3-30 characters and use letters, numbers, or hyphens.
- The deploy script stores Azure OpenAI secrets in Key Vault and creates a Databricks secret scope (default: aoai-scope).
- The compute stack also creates a Key Vault-backed Databricks secret scope for SP credentials (default: dbx-sp-scope).
- The access connector uses a managed identity and storage RBAC to avoid storage secrets in Key Vault.
- In notebooks, read secrets with dbutils.secrets.get("aoai-scope", "openai-api-base"), openai-api-key, openai-api-version, and openai-deployment-name.
- The deploy script grants Key Vault access to the Azure Databricks service principal (app id 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d).
- The Databricks compute stack installs the OpenAI SDK and Databricks Vector Search via cluster libraries.
- The Unity Catalog stack requires your Databricks account ID (set in scripts/deploy.py DEFAULTS or in terraform/09_unity_catalog/terraform.tfvars).
- If your account already has a metastore in the workspace region, set existing_metastore_id to reuse it instead of creating a new one.
- Grant the Databricks SP USE CATALOG/SCHEMA and SELECT on the UC tables used by Vector Search, plus permissions on the Vector Search endpoint/index.
- Create the serving endpoint only after registering a model version in MLflow/Unity Catalog.
- If Terraform reports an unsupported Databricks resource, run `terraform init -upgrade` in that stack to pull a newer provider.
- The serving endpoint injects Databricks OAuth + Azure OpenAI env vars via Key Vault-backed scopes (DATABRICKS_HOST/AUTH_TYPE/CLIENT_ID/CLIENT_SECRET/TENANT_ID and AZURE_OPENAI_ENDPOINT/API_KEY/API_VERSION).
- The notebook uses the workspace MLflow registry (`mlflow.set_registry_uri("databricks")`). Switch this if you plan to use Unity Catalog.
- Names are built from prefixes plus a random pet name by default. Override variables if needed.
- The .env and terraform.tfvars files are gitignored.
