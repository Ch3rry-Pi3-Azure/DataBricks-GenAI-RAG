# Azure OpenAI + Databricks Generative AI

Terraform-driven setup for a resource group, Azure OpenAI account + deployment, storage account + container, Key Vault + secrets, and Azure Databricks workspace + compute.

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

The deploy script also uploads `data/diabetes_treatment_faq.csv` to the storage container.

4) Open the notebook in Databricks and run the registration cell:
- `notebooks/RAG.ipynb` (registers model as `rag_model`)

5) Sync secrets to Key Vault (if `DATABRICKS_TOKEN` is not set, deploy.py will auto-create a PAT for serving):
```powershell
python scripts\deploy.py --keyvault-only
```

6) Deploy the serving endpoint:
```powershell
python scripts\deploy.py --serving-only
```

7) Query the endpoint (example payload):
```json
{
  "dataframe_split": {
    "columns": ["user_query"],
    "data": [["hello how are you?"]]
  }
}
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
python scripts\deploy.py --storage-only
python scripts\deploy.py --access-connector-only
python scripts\deploy.py --uc-only
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --serving-only
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
python scripts\destroy.py --compute-only
python scripts\destroy.py --notebooks-only
python scripts\destroy.py --serving-only
```

## Guide
See guides/setup.md for detailed instructions.
