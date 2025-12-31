import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULTS = {
    "resource_group_name_prefix": "rg-dbgenai",
    "location": "eastus2",
    "account_name_prefix": "aoaidbgenai",
    "sku_name": "S0",
    "deployment_name": "gpt-5-chat",
    "model_name": "gpt-5-chat",
    "model_version": "2025-10-03",
    "scale_type": "GlobalStandard",
    "deployment_capacity": 1,
    "openai_api_version": "2024-02-15-preview",
    "workspace_name_prefix": "adb-genai",
    "databricks_sku": "premium",
    "key_vault_name_prefix": "kvdbgenai",
    "key_vault_sku_name": "standard",
    "secret_scope_name": "aoai-scope",
    "databricks_pat_secret_name": "databricks-pat",
    "auto_create_databricks_pat": True,
    "databricks_pat_lifetime_days": 90,
    "databricks_pat_comment": "deploy.py serving PAT",
    "openai_pypi_package": "openai==1.56.0",
    "vectorsearch_pypi_package": "databricks-vectorsearch",
    "use_ml_runtime": True,
    "storage_account_name_prefix": "stgdbgenai",
    "storage_container_name": "rag-data",
    "storage_is_hns_enabled": True,
    "storage_account_tier": "Standard",
    "storage_account_replication_type": "LRS",
    "storage_grant_current_principal_access": True,
    "access_connector_name_prefix": "dbac-genai",
    "databricks_account_id": "24237807-b0da-4ee9-8908-110accb095ca",
    "metastore_name_prefix": "uc-metastore",
    "existing_metastore_id": None,
    "storage_credential_name": "uc-storage-credential",
    "external_location_name": "uc-external-location",
    "serving_endpoint_name": "rag-model-endpoint",
    "serving_model_name": None,
    "serving_model_suffix": "rag_model",
    "serving_served_model_name": "rag-model",
    "serving_model_version": None,
    "serving_workload_size": "Small",
    "serving_scale_to_zero": True,
    "serving_traffic_percentage": 100,
}

ENV_KEYS = [
    "OPENAI_API_BASE",
    "OPENAI_API_KEY",
    "OPENAI_API_VERSION",
    "OPENAI_DEPLOYMENT_NAME",
    "DATABRICKS_WORKSPACE_URL",
    "DATABRICKS_TOKEN",
]

DATABRICKS_SP_APP_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
ACCOUNT_HOST = "https://accounts.azuredatabricks.net"
KEY_VAULT_SECRET_NAMES = {
    "OPENAI_API_BASE": "openai-api-base",
    "OPENAI_API_KEY": "openai-api-key",
    "OPENAI_API_VERSION": "openai-api-version",
    "OPENAI_DEPLOYMENT_NAME": "openai-deployment-name",
    "DATABRICKS_TOKEN": DEFAULTS["databricks_pat_secret_name"],
}
AZ_FALLBACK_PATHS = [
    r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
]

def find_az():
    az_path = shutil.which("az")
    if az_path:
        return az_path
    for path in AZ_FALLBACK_PATHS:
        if Path(path).exists():
            return path
    return None

AZ_BIN = find_az()

def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd)

def run_capture(cmd):
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.check_output(cmd, text=True).strip()

def run_sensitive(cmd, redacted_indices):
    display_cmd = cmd[:]
    for index in redacted_indices:
        if 0 <= index < len(display_cmd):
            display_cmd[index] = "***"
    print(f"\n$ {' '.join(display_cmd)}")
    subprocess.check_call(cmd)

def run_apply_with_import(tf_dir, deployment_id):
    cmd = ["terraform", f"-chdir={tf_dir}", "apply", "-auto-approve"]
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        return
    combined = (result.stdout or "") + (result.stderr or "")
    if "already exists" in combined and "azurerm_cognitive_deployment" in combined:
        run(["terraform", f"-chdir={tf_dir}", "import", "azurerm_cognitive_deployment.main", deployment_id])
        run(cmd)
        return
    raise subprocess.CalledProcessError(result.returncode, cmd)

def hcl_value(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace('"', '\\"')
    return f'"{escaped}"'

def write_tfvars(path, items):
    lines = [f"{key} = {hcl_value(value)}" for key, value in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def get_output(tf_dir, output_name):
    return run_capture(["terraform", f"-chdir={tf_dir}", "output", "-raw", output_name])

def get_output_optional(tf_dir, output_name):
    try:
        return get_output(tf_dir, output_name)
    except subprocess.CalledProcessError:
        return None

def get_output_with_apply(tf_dir, output_name):
    try:
        return get_output(tf_dir, output_name)
    except subprocess.CalledProcessError:
        run(["terraform", f"-chdir={tf_dir}", "apply", "-auto-approve"])
        return get_output(tf_dir, output_name)

def write_rg_tfvars(rg_dir):
    items = [
        ("resource_group_name", None),
        ("resource_group_name_prefix", DEFAULTS["resource_group_name_prefix"]),
        ("location", DEFAULTS["location"]),
    ]
    write_tfvars(rg_dir / "terraform.tfvars", items)

def write_openai_tfvars(openai_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("account_name_prefix", DEFAULTS["account_name_prefix"]),
        ("sku_name", DEFAULTS["sku_name"]),
    ]
    write_tfvars(openai_dir / "terraform.tfvars", items)

def write_deployment_tfvars(deployment_dir, rg_name, account_name):
    items = [
        ("resource_group_name", rg_name),
        ("account_name", account_name),
        ("deployment_name", DEFAULTS["deployment_name"]),
        ("model_name", DEFAULTS["model_name"]),
        ("model_version", DEFAULTS["model_version"]),
        ("scale_type", DEFAULTS["scale_type"]),
        ("deployment_capacity", DEFAULTS["deployment_capacity"]),
    ]
    write_tfvars(deployment_dir / "terraform.tfvars", items)

def write_key_vault_tfvars(kv_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("key_vault_name_prefix", DEFAULTS["key_vault_name_prefix"]),
        ("sku_name", DEFAULTS["key_vault_sku_name"]),
    ]
    write_tfvars(kv_dir / "terraform.tfvars", items)

def write_databricks_tfvars(databricks_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("workspace_name_prefix", DEFAULTS["workspace_name_prefix"]),
        ("sku", DEFAULTS["databricks_sku"]),
        ("managed_resource_group_name", None),
    ]
    write_tfvars(databricks_dir / "terraform.tfvars", items)

def write_storage_tfvars(storage_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("storage_account_name", None),
        ("storage_account_name_prefix", DEFAULTS["storage_account_name_prefix"]),
        ("container_name", DEFAULTS["storage_container_name"]),
        ("is_hns_enabled", DEFAULTS["storage_is_hns_enabled"]),
        ("account_tier", DEFAULTS["storage_account_tier"]),
        ("account_replication_type", DEFAULTS["storage_account_replication_type"]),
        ("grant_current_principal_access", DEFAULTS["storage_grant_current_principal_access"]),
    ]
    write_tfvars(storage_dir / "terraform.tfvars", items)

def write_access_connector_tfvars(access_connector_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("access_connector_name", None),
        ("access_connector_name_prefix", DEFAULTS["access_connector_name_prefix"]),
    ]
    write_tfvars(access_connector_dir / "terraform.tfvars", items)

def write_unity_catalog_tfvars(unity_dir, rg_name, workspace_id, existing_metastore_id):
    items = [
        ("resource_group_name", rg_name),
        ("databricks_account_id", DEFAULTS["databricks_account_id"]),
        ("workspace_id", workspace_id),
        ("metastore_name", None),
        ("existing_metastore_id", existing_metastore_id),
        ("metastore_name_prefix", DEFAULTS["metastore_name_prefix"]),
        ("metastore_region", None),
        ("metastore_storage_root", None),
        ("default_catalog_name", "main"),
        ("metastore_data_access_name", "metastore-access"),
        ("storage_credential_name", DEFAULTS["storage_credential_name"]),
        ("external_location_name", DEFAULTS["external_location_name"]),
        ("external_location_url", None),
    ]
    write_tfvars(unity_dir / "terraform.tfvars", items)

def write_databricks_compute_tfvars(compute_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("secret_scope_name", DEFAULTS["secret_scope_name"]),
        ("openai_pypi_package", DEFAULTS["openai_pypi_package"]),
        ("vectorsearch_pypi_package", DEFAULTS["vectorsearch_pypi_package"]),
        ("use_ml_runtime", DEFAULTS["use_ml_runtime"]),
    ]
    write_tfvars(compute_dir / "terraform.tfvars", items)

def write_notebooks_tfvars(notebooks_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
    ]
    write_tfvars(notebooks_dir / "terraform.tfvars", items)

def write_serving_tfvars(serving_dir, rg_name, databricks_dir):
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    run(["terraform", f"-chdir={databricks_dir}", "init"])
    workspace_url = get_output(databricks_dir, "databricks_workspace_url")
    token = get_databricks_aad_token()
    model_name = DEFAULTS["serving_model_name"]
    if model_name is None:
        model_name = find_registered_model_name(workspace_url, token, DEFAULTS["serving_model_suffix"])
    if model_name is None:
        raise RuntimeError(
            f"Could not find any model versions for '*.{DEFAULTS['serving_model_suffix']}' or '{DEFAULTS['serving_model_suffix']}'. "
            "Register the model in MLflow before deploying the serving endpoint or set serving_model_name."
        )
    model_version = DEFAULTS["serving_model_version"]
    if model_version is None:
        model_version = get_latest_model_version(workspace_url, token, model_name)
        if model_version is None:
            raise RuntimeError(
                f"Could not find any model versions for '{model_name}'. "
                "Register the model in MLflow before deploying the serving endpoint."
            )
    items = [
        ("resource_group_name", rg_name),
        ("endpoint_name", DEFAULTS["serving_endpoint_name"]),
        ("served_model_name", DEFAULTS["serving_served_model_name"]),
        ("model_name", model_name),
        ("model_version", model_version),
        ("secret_scope_name", DEFAULTS["secret_scope_name"]),
        ("databricks_pat_secret_name", DEFAULTS["databricks_pat_secret_name"]),
        ("workload_size", DEFAULTS["serving_workload_size"]),
        ("scale_to_zero_enabled", DEFAULTS["serving_scale_to_zero"]),
        ("traffic_percentage", DEFAULTS["serving_traffic_percentage"]),
    ]
    write_tfvars(serving_dir / "terraform.tfvars", items)

def upload_seed_data(storage_dir, repo_root):
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    data_file = repo_root / "data" / "diabetes_treatment_faq.csv"
    if not data_file.exists():
        print(f"\nNo seed data found at {data_file}, skipping upload.")
        return
    storage_account = get_output(storage_dir, "storage_account_name")
    container_name = get_output(storage_dir, "storage_container_name")
    run(
        [
            AZ_BIN,
            "storage",
            "blob",
            "upload",
            "--account-name",
            storage_account,
            "--container-name",
            container_name,
            "--file",
            str(data_file),
            "--name",
            data_file.name,
            "--auth-mode",
            "login",
            "--overwrite",
            "true",
        ]
    )

def normalize_workspace_url(url):
    if not url:
        return url
    if url.startswith("https://"):
        return url
    return f"https://{url}"

def read_env_file(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values

def load_env_file_into_env(repo_root):
    values = read_env_file(repo_root / ".env")
    for key, value in values.items():
        os.environ.setdefault(key, value)

def parse_bool_env(value, default):
    if value is None:
        return default
    value = value.strip().lower()
    if value in ("1", "true", "yes", "y", "on"):
        return True
    if value in ("0", "false", "no", "n", "off"):
        return False
    return default

def auto_create_databricks_pat_enabled():
    env_value = os.environ.get("DATABRICKS_AUTO_PAT") or os.environ.get("AUTO_CREATE_DATABRICKS_PAT")
    return parse_bool_env(env_value, DEFAULTS["auto_create_databricks_pat"])

def key_vault_secret_exists(vault_name, secret_name):
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    cmd = [
        AZ_BIN,
        "keyvault",
        "secret",
        "show",
        "--vault-name",
        vault_name,
        "--name",
        secret_name,
        "--query",
        "id",
        "-o",
        "tsv",
    ]
    try:
        output = run_capture(cmd)
    except subprocess.CalledProcessError:
        return False
    return bool(output)

def create_databricks_pat(workspace_url, lifetime_days, comment):
    token = get_databricks_aad_token()
    payload = {"comment": comment}
    if lifetime_days is not None:
        lifetime_seconds = int(lifetime_days) * 86400
        if lifetime_seconds > 0:
            payload["lifetime_seconds"] = lifetime_seconds
    response = databricks_api(workspace_url, token, "POST", "/api/2.0/token/create", payload)
    token_value = response.get("token_value")
    if not token_value:
        raise RuntimeError(f"Databricks token create did not return token_value: {response}")
    return token_value

def resolve_databricks_token(vault_name, databricks_dir, workspace_url=None):
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return token
    if not auto_create_databricks_pat_enabled():
        return None
    secret_name = DEFAULTS["databricks_pat_secret_name"]
    if key_vault_secret_exists(vault_name, secret_name):
        print(f"\nKey Vault secret '{secret_name}' already exists; skipping PAT creation.")
        return None
    if workspace_url is None:
        workspace_url = get_output_optional(databricks_dir, "databricks_workspace_url")
    if not workspace_url:
        raise RuntimeError("Cannot auto-create Databricks PAT because workspace URL is unavailable. Set DATABRICKS_TOKEN or deploy the Databricks workspace.")
    print("\nCreating a Databricks PAT for serving...")
    try:
        return create_databricks_pat(
            workspace_url,
            DEFAULTS["databricks_pat_lifetime_days"],
            DEFAULTS["databricks_pat_comment"],
        )
    except RuntimeError as exc:
        raise RuntimeError(
            "Failed to auto-create a Databricks PAT. "
            "Set DATABRICKS_TOKEN or disable auto creation with AUTO_CREATE_DATABRICKS_PAT=0."
        ) from exc

def write_env_file(
    repo_root,
    openai_endpoint=None,
    openai_key=None,
    api_version=None,
    deployment_name=None,
    workspace_url=None,
):
    env_path = repo_root / ".env"
    values = read_env_file(env_path)
    if openai_endpoint is not None:
        values["OPENAI_API_BASE"] = openai_endpoint
    if openai_key is not None:
        values["OPENAI_API_KEY"] = openai_key
    if api_version is not None:
        values["OPENAI_API_VERSION"] = api_version
    if deployment_name is not None:
        values["OPENAI_DEPLOYMENT_NAME"] = deployment_name
    if workspace_url is not None:
        values["DATABRICKS_WORKSPACE_URL"] = normalize_workspace_url(workspace_url)
    if not values:
        return
    lines = [f"{key}={values[key]}" for key in ENV_KEYS if key in values]
    for key in sorted(values):
        if key in ENV_KEYS:
            continue
        lines.append(f"{key}={values[key]}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def set_databricks_kv_policy(vault_name):
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    run(
        [
            AZ_BIN,
            "keyvault",
            "set-policy",
            "--name",
            vault_name,
            "--spn",
            DATABRICKS_SP_APP_ID,
            "--secret-permissions",
            "get",
            "list",
        ]
    )

def set_key_vault_secret(vault_name, secret_name, secret_value):
    if secret_value is None:
        return
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    cmd = [
        AZ_BIN,
        "keyvault",
        "secret",
        "set",
        "--vault-name",
        vault_name,
        "--name",
        secret_name,
        "--value",
        secret_value,
    ]
    run_sensitive(cmd, redacted_indices=[len(cmd) - 1])

def sync_key_vault_secrets(vault_name, endpoint, api_key, api_version, deployment_name, databricks_token=None):
    set_key_vault_secret(vault_name, KEY_VAULT_SECRET_NAMES["OPENAI_API_BASE"], endpoint)
    set_key_vault_secret(vault_name, KEY_VAULT_SECRET_NAMES["OPENAI_API_KEY"], api_key)
    set_key_vault_secret(vault_name, KEY_VAULT_SECRET_NAMES["OPENAI_API_VERSION"], api_version)
    set_key_vault_secret(
        vault_name,
        KEY_VAULT_SECRET_NAMES["OPENAI_DEPLOYMENT_NAME"],
        deployment_name,
    )
    set_key_vault_secret(vault_name, KEY_VAULT_SECRET_NAMES["DATABRICKS_TOKEN"], databricks_token)

def get_databricks_aad_token():
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    return run_capture(
        [
            AZ_BIN,
            "account",
            "get-access-token",
            "--resource",
            DATABRICKS_SP_APP_ID,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ]
    )

def normalize_databricks_host(host):
    if not host:
        return host
    return host if host.startswith("https://") else f"https://{host}"

def databricks_api(host, token, method, path, payload=None):
    url = f"{normalize_databricks_host(host).rstrip('/')}{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Databricks API error {exc.code}: {detail}") from exc

def get_latest_model_version(host, token, model_name):
    paths = [
        ("/api/2.0/mlflow/registered-models/get-latest-versions", {"name": model_name}),
        ("/api/2.0/mlflow/model-versions/search", {"filter": f"name='{model_name}'"}),
        ("/api/2.0/preview/mlflow/model-versions/search", {"filter": f"name='{model_name}'"}),
    ]
    versions = []
    last_error = None
    for path, payload in paths:
        try:
            response = databricks_api(host, token, "POST", path, payload)
        except RuntimeError as exc:
            last_error = exc
            if "ENDPOINT_NOT_FOUND" in str(exc):
                continue
            raise
        items = response.get("model_versions", [])
        for item in items:
            version = item.get("version")
            if version is not None:
                try:
                    versions.append(int(version))
                except ValueError:
                    continue
        if versions:
            return str(max(versions))
    # Fallback to Unity Catalog model versions API.
    try:
        uc_versions = databricks_api(
            host,
            token,
            "GET",
            f"/api/2.1/unity-catalog/models/{model_name}/versions?max_results=100",
        )
        for item in uc_versions.get("model_versions", []):
            version = item.get("version")
            if version is not None:
                try:
                    versions.append(int(version))
                except ValueError:
                    continue
        if versions:
            return str(max(versions))
    except RuntimeError as exc:
        if "ENDPOINT_NOT_FOUND" not in str(exc):
            raise
    if last_error is not None and "ENDPOINT_NOT_FOUND" in str(last_error):
        return None
    if last_error is not None:
        raise last_error
    return None

def list_registered_models(host, token):
    try:
        response = databricks_api(host, token, "GET", "/api/2.0/mlflow/registered-models/list")
    except RuntimeError as exc:
        if "ENDPOINT_NOT_FOUND" in str(exc):
            return []
        raise
    return response.get("registered_models", [])

def list_uc_models(host, token):
    models = []
    page_token = None
    while True:
        path = "/api/2.1/unity-catalog/models"
        if page_token:
            path = f"{path}?page_token={page_token}"
        response = databricks_api(host, token, "GET", path)
        items = response.get("registered_models", [])
        models.extend(items)
        page_token = response.get("next_page_token")
        if not page_token:
            break
    return models

def find_registered_model_name(host, token, model_suffix):
    payloads = [
        {"filter": f"name LIKE '%.{model_suffix}'"},
        {"filter": f"name = '{model_suffix}'"},
    ]
    names = []
    for payload in payloads:
        try:
            response = databricks_api(host, token, "POST", "/api/2.0/mlflow/registered-models/search", payload)
        except RuntimeError as exc:
            if "ENDPOINT_NOT_FOUND" in str(exc) or "INVALID_PARAMETER_VALUE" in str(exc):
                continue
            raise
        items = response.get("registered_models", [])
        for item in items:
            name = item.get("name")
            if name:
                names.append(name)
        if names:
            break
    if not names:
        items = list_registered_models(host, token)
        for item in items:
            name = item.get("name")
            if not name:
                continue
            if name == model_suffix or name.endswith(f".{model_suffix}"):
                names.append(name)
    if not names:
        for item in list_uc_models(host, token):
            name = item.get("full_name") or item.get("name")
            if not name:
                continue
            if name == model_suffix or name.endswith(f".{model_suffix}"):
                names.append(name)
    if not names:
        for payload in (
            {"filter": f"name = '{model_suffix}'"},
            {"filter": f"name LIKE '%.{model_suffix}'"},
        ):
            try:
                response = databricks_api(host, token, "POST", "/api/2.0/mlflow/model-versions/search", payload)
            except RuntimeError as exc:
                if "ENDPOINT_NOT_FOUND" in str(exc) or "INVALID_PARAMETER_VALUE" in str(exc):
                    continue
                raise
            items = response.get("model_versions", [])
            for item in items:
                name = item.get("name")
                if name:
                    names.append(name)
            if names:
                break
    if not names:
        return None
    unique = sorted(set(names))
    if len(unique) > 1:
        raise RuntimeError(f"Multiple models found matching '*.{model_suffix}': {', '.join(unique)}. Set serving_model_name explicitly.")
    return unique[0]

def get_workspace_location_from_state(databricks_dir):
    state_path = Path(databricks_dir) / "terraform.tfstate"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for resource in state.get("resources", []):
        if resource.get("type") != "azurerm_databricks_workspace":
            continue
        for instance in resource.get("instances", []):
            location = (instance.get("attributes") or {}).get("location")
            if location:
                return location
    return None

def get_databricks_workspace_id(account_id, token, workspace_name):
    response = databricks_api(
        ACCOUNT_HOST,
        token,
        "GET",
        f"/api/2.0/accounts/{account_id}/workspaces",
    )
    if isinstance(response, list):
        workspaces = response
    else:
        workspaces = response.get("workspaces") or response.get("items") or []
    for workspace in workspaces:
        if workspace.get("workspace_name") == workspace_name or workspace.get("name") == workspace_name:
            workspace_id = workspace.get("workspace_id") or workspace.get("id")
            if workspace_id is None:
                break
            return int(workspace_id)
    raise RuntimeError(f"Workspace '{workspace_name}' not found in Databricks account {account_id}.")

def get_databricks_metastore_id(account_id, token, region=None, name=None):
    response = databricks_api(
        ACCOUNT_HOST,
        token,
        "GET",
        f"/api/2.0/accounts/{account_id}/metastores",
    )
    if isinstance(response, list):
        metastores = response
    else:
        metastores = response.get("metastores") or response.get("items") or []
    matches = metastores
    if name:
        matches = [ms for ms in matches if ms.get("name") == name]
    if region:
        region_lower = str(region).lower()
        matches = [ms for ms in matches if str(ms.get("region", "")).lower() == region_lower]
    if not matches:
        return None
    if len(matches) > 1:
        options = ", ".join(f"{ms.get('name')}:{ms.get('metastore_id')}" for ms in matches)
        raise RuntimeError(f"Multiple metastores found for region '{region}': {options}. Set existing_metastore_id explicitly.")
    return matches[0].get("metastore_id")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Deploy Terraform stacks for Azure OpenAI and Databricks.")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--rg-only", action="store_true", help="Deploy only the resource group stack")
        group.add_argument("--openai-only", action="store_true", help="Deploy only the Azure OpenAI account stack")
        group.add_argument("--deployment-only", action="store_true", help="Deploy only the Azure OpenAI deployment stack")
        group.add_argument("--databricks-only", action="store_true", help="Deploy only the Databricks workspace stack")
        group.add_argument("--keyvault-only", action="store_true", help="Deploy only the Key Vault stack")
        group.add_argument("--storage-only", action="store_true", help="Deploy only the storage stack")
        group.add_argument("--access-connector-only", action="store_true", help="Deploy only the Databricks access connector stack")
        group.add_argument("--uc-only", action="store_true", help="Deploy only the Unity Catalog stack")
        group.add_argument("--compute-only", action="store_true", help="Deploy only the Databricks compute stack")
        group.add_argument("--notebooks-only", action="store_true", help="Deploy only the notebooks stack")
        group.add_argument("--serving-only", action="store_true", help="Deploy only the serving endpoint stack")
        args = parser.parse_args()

        repo_root = Path(__file__).resolve().parent.parent
        load_env_file_into_env(repo_root)
        rg_dir = repo_root / "terraform" / "01_resource_group"
        openai_dir = repo_root / "terraform" / "02_azure_openai"
        deployment_dir = repo_root / "terraform" / "03_openai_deployment"
        databricks_dir = repo_root / "terraform" / "04_databricks_workspace"
        key_vault_dir = repo_root / "terraform" / "05_key_vault"
        storage_dir = repo_root / "terraform" / "09_storage"
        access_connector_dir = repo_root / "terraform" / "10_access_connector"
        unity_dir = repo_root / "terraform" / "11_unity_catalog"
        compute_dir = repo_root / "terraform" / "06_databricks_compute"
        notebooks_dir = repo_root / "terraform" / "07_notebooks"
        serving_dir = repo_root / "terraform" / "08_serving_endpoint"

        if args.rg_only:
            write_rg_tfvars(rg_dir)
            run(["terraform", f"-chdir={rg_dir}", "init"])
            run(["terraform", f"-chdir={rg_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.openai_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_openai_tfvars(openai_dir, rg_name)
            run(["terraform", f"-chdir={openai_dir}", "init"])
            run(["terraform", f"-chdir={openai_dir}", "apply", "-auto-approve"])
            endpoint = get_output(openai_dir, "openai_endpoint")
            api_key = get_output_with_apply(openai_dir, "openai_primary_key")
            write_env_file(
                repo_root,
                openai_endpoint=endpoint,
                openai_key=api_key,
                api_version=DEFAULTS["openai_api_version"],
                deployment_name=DEFAULTS["deployment_name"],
            )
            sys.exit(0)

        if args.deployment_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            run(["terraform", f"-chdir={openai_dir}", "init"])
            account_name = get_output(openai_dir, "openai_account_name")
            account_id = get_output(openai_dir, "openai_account_id")
            endpoint = get_output(openai_dir, "openai_endpoint")
            api_key = get_output_with_apply(openai_dir, "openai_primary_key")
            write_deployment_tfvars(deployment_dir, rg_name, account_name)
            run(["terraform", f"-chdir={deployment_dir}", "init"])
            deployment_id = f"{account_id}/deployments/{DEFAULTS['deployment_name']}"
            run_apply_with_import(deployment_dir, deployment_id)
            write_env_file(
                repo_root,
                openai_endpoint=endpoint,
                openai_key=api_key,
                api_version=DEFAULTS["openai_api_version"],
                deployment_name=DEFAULTS["deployment_name"],
            )
            sys.exit(0)

        if args.databricks_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_databricks_tfvars(databricks_dir, rg_name)
            run(["terraform", f"-chdir={databricks_dir}", "init"])
            run(["terraform", f"-chdir={databricks_dir}", "apply", "-auto-approve"])
            workspace_url = get_output(databricks_dir, "databricks_workspace_url")
            write_env_file(repo_root, workspace_url=workspace_url)
            sys.exit(0)

        if args.keyvault_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_key_vault_tfvars(key_vault_dir, rg_name)
            run(["terraform", f"-chdir={key_vault_dir}", "init"])
            run(["terraform", f"-chdir={key_vault_dir}", "apply", "-auto-approve"])
            vault_name = get_output(key_vault_dir, "key_vault_name")
            set_databricks_kv_policy(vault_name)
            endpoint = get_output_optional(openai_dir, "openai_endpoint")
            api_key = get_output_optional(openai_dir, "openai_primary_key")
            openai_api_version = DEFAULTS["openai_api_version"] if endpoint and api_key else None
            deployment_name = DEFAULTS["deployment_name"] if endpoint and api_key else None
            databricks_token = resolve_databricks_token(vault_name, databricks_dir)
            sync_key_vault_secrets(
                vault_name,
                endpoint,
                api_key,
                openai_api_version,
                deployment_name,
                databricks_token=databricks_token,
            )
            sys.exit(0)

        if args.storage_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_storage_tfvars(storage_dir, rg_name)
            run(["terraform", f"-chdir={storage_dir}", "init"])
            run(["terraform", f"-chdir={storage_dir}", "apply", "-auto-approve"])
            upload_seed_data(storage_dir, repo_root)
            sys.exit(0)

        if args.access_connector_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_access_connector_tfvars(access_connector_dir, rg_name)
            run(["terraform", f"-chdir={access_connector_dir}", "init"])
            run(["terraform", f"-chdir={access_connector_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.uc_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            run(["terraform", f"-chdir={databricks_dir}", "init"])
            workspace_name = get_output(databricks_dir, "databricks_workspace_name")
            token = get_databricks_aad_token()
            workspace_id = get_databricks_workspace_id(DEFAULTS["databricks_account_id"], token, workspace_name)
            workspace_location = get_workspace_location_from_state(databricks_dir) or DEFAULTS["location"]
            existing_metastore_id = DEFAULTS["existing_metastore_id"] or get_databricks_metastore_id(
                DEFAULTS["databricks_account_id"],
                token,
                region=workspace_location,
            )
            write_unity_catalog_tfvars(unity_dir, rg_name, workspace_id, existing_metastore_id)
            run(["terraform", f"-chdir={unity_dir}", "init"])
            run(["terraform", f"-chdir={unity_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.compute_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_databricks_compute_tfvars(compute_dir, rg_name)
            run(["terraform", f"-chdir={compute_dir}", "init"])
            run(["terraform", f"-chdir={compute_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.notebooks_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_notebooks_tfvars(notebooks_dir, rg_name)
            run(["terraform", f"-chdir={notebooks_dir}", "init"])
            run(["terraform", f"-chdir={notebooks_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.serving_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_serving_tfvars(serving_dir, rg_name, databricks_dir)
            run(["terraform", f"-chdir={serving_dir}", "init"])
            run(["terraform", f"-chdir={serving_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        write_rg_tfvars(rg_dir)
        run(["terraform", f"-chdir={rg_dir}", "init"])
        run(["terraform", f"-chdir={rg_dir}", "apply", "-auto-approve"])
        rg_name = get_output(rg_dir, "resource_group_name")

        write_openai_tfvars(openai_dir, rg_name)
        run(["terraform", f"-chdir={openai_dir}", "init"])
        run(["terraform", f"-chdir={openai_dir}", "apply", "-auto-approve"])
        account_name = get_output(openai_dir, "openai_account_name")
        account_id = get_output(openai_dir, "openai_account_id")
        endpoint = get_output(openai_dir, "openai_endpoint")
        api_key = get_output_with_apply(openai_dir, "openai_primary_key")

        write_deployment_tfvars(deployment_dir, rg_name, account_name)
        run(["terraform", f"-chdir={deployment_dir}", "init"])
        deployment_id = f"{account_id}/deployments/{DEFAULTS['deployment_name']}"
        run_apply_with_import(deployment_dir, deployment_id)

        write_databricks_tfvars(databricks_dir, rg_name)
        run(["terraform", f"-chdir={databricks_dir}", "init"])
        run(["terraform", f"-chdir={databricks_dir}", "apply", "-auto-approve"])
        workspace_url = get_output(databricks_dir, "databricks_workspace_url")

        write_key_vault_tfvars(key_vault_dir, rg_name)
        run(["terraform", f"-chdir={key_vault_dir}", "init"])
        run(["terraform", f"-chdir={key_vault_dir}", "apply", "-auto-approve"])
        vault_name = get_output(key_vault_dir, "key_vault_name")
        set_databricks_kv_policy(vault_name)
        databricks_token = resolve_databricks_token(vault_name, databricks_dir, workspace_url=workspace_url)
        sync_key_vault_secrets(
            vault_name,
            endpoint,
            api_key,
            DEFAULTS["openai_api_version"],
            DEFAULTS["deployment_name"],
            databricks_token=databricks_token,
        )

        write_storage_tfvars(storage_dir, rg_name)
        run(["terraform", f"-chdir={storage_dir}", "init"])
        run(["terraform", f"-chdir={storage_dir}", "apply", "-auto-approve"])
        upload_seed_data(storage_dir, repo_root)

        write_access_connector_tfvars(access_connector_dir, rg_name)
        run(["terraform", f"-chdir={access_connector_dir}", "init"])
        run(["terraform", f"-chdir={access_connector_dir}", "apply", "-auto-approve"])

        workspace_name = get_output(databricks_dir, "databricks_workspace_name")
        token = get_databricks_aad_token()
        workspace_id = get_databricks_workspace_id(DEFAULTS["databricks_account_id"], token, workspace_name)
        workspace_location = get_workspace_location_from_state(databricks_dir) or DEFAULTS["location"]
        existing_metastore_id = DEFAULTS["existing_metastore_id"] or get_databricks_metastore_id(
            DEFAULTS["databricks_account_id"],
            token,
            region=workspace_location,
        )
        write_unity_catalog_tfvars(unity_dir, rg_name, workspace_id, existing_metastore_id)
        run(["terraform", f"-chdir={unity_dir}", "init"])
        run(["terraform", f"-chdir={unity_dir}", "apply", "-auto-approve"])

        write_databricks_compute_tfvars(compute_dir, rg_name)
        run(["terraform", f"-chdir={compute_dir}", "init"])
        run(["terraform", f"-chdir={compute_dir}", "apply", "-auto-approve"])

        write_notebooks_tfvars(notebooks_dir, rg_name)
        run(["terraform", f"-chdir={notebooks_dir}", "init"])
        run(["terraform", f"-chdir={notebooks_dir}", "apply", "-auto-approve"])
        write_env_file(
            repo_root,
            openai_endpoint=endpoint,
            openai_key=api_key,
            api_version=DEFAULTS["openai_api_version"],
            deployment_name=DEFAULTS["deployment_name"],
            workspace_url=workspace_url,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(exc.returncode)
