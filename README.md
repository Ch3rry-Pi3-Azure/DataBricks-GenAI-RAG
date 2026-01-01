# Azure Databricks RAG (Azure OpenAI + Vector Search)

Terraform-driven setup for a RAG application on Azure: resource group, Azure OpenAI account + deployment, storage account + container (HNS enabled), Key Vault + secrets, Databricks workspace + compute, access connector + storage RBAC, Unity Catalog external location, and model serving.

## Quick Start
1) Install prerequisites:
   - Azure CLI (az)
   - Terraform (>= 1.5)
   - Python 3.10+

2) Authenticate to Azure:
```powershell
az login
az account show
```

3) Deploy infrastructure:
```powershell
python scripts\deploy.py
```

The deploy script uploads `data/diabetes_treatment_faq.csv` to the storage container.

4) Open the notebook in Databricks and run the RAG flow:
- `notebooks/RAG.ipynb` (loads data from the UC external volume, builds the table + index, registers `rag_model`)

5) Export Databricks SP credentials and sync secrets to Key Vault:
```powershell
$env:DATABRICKS_CLIENT_ID = "<app-id>"
$env:DATABRICKS_CLIENT_SECRET = "<client-secret>"
$env:DATABRICKS_TENANT_ID = "<tenant-id>"
python scripts\deploy.py --sp-only
python scripts\deploy.py --keyvault-only
```
`--sp-only` now creates the SP at both the account and workspace level so Unity Catalog can grant permissions.

If you want this automated (create/rotate the SP secret + sync Key Vault):
```powershell
python scripts\deploy.py --sp-bootstrap
```
This uses Azure CLI to create or rotate the SP secret and writes the values into `.env`.

6) Deploy the serving endpoint:
```powershell
python scripts\deploy.py --serving-only
```

7) Query the endpoint (example payload):
```json
{
  "dataframe_records": [
    { "query": "what is diabetes?" }
  ]
}
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
- scripts/: Deploy/destroy helpers (auto-writes terraform.tfvars and .env)
- guides/setup.md: Detailed setup guide
- notebooks/: Databricks notebooks (tracked)

## Deploy/Destroy Options
Deploy specific stacks:
```powershell
python scripts\deploy.py --rg-only
python scripts\deploy.py --openai-only
python scripts\deploy.py --deployment-only
python scripts\deploy.py --databricks-only
python scripts\deploy.py --keyvault-only
python scripts\deploy.py --sp-only
python scripts\deploy.py --sp-bootstrap
python scripts\deploy.py --storage-only
python scripts\deploy.py --access-connector-only
python scripts\deploy.py --uc-only
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --serving-only
python scripts\deploy.py --vector-perms-only
python scripts\deploy.py --uc-grants-only
```

Destroy:
```powershell
python scripts\destroy.py
```

Destroy specific stacks:
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

## Guide
See guides/setup.md for detailed instructions.
