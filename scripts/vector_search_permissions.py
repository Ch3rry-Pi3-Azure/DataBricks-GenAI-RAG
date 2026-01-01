import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

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


def run_capture(cmd):
    return subprocess.check_output(cmd, text=True).strip()


def get_token(resource):
    az_bin = find_az()
    if az_bin is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    return run_capture(
        [
            az_bin,
            "account",
            "get-access-token",
            "--resource",
            resource,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ]
    )


def request_json(method, url, token, headers=None, payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    if headers:
        for key, value in headers.items():
            if value:
                req.add_header(key, value)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Databricks API error {exc.code}: {detail}") from exc


def normalize_host(host):
    if not host:
        return host
    return host if host.startswith("https://") else f"https://{host}"


def resolve_endpoint(endpoints, name):
    if isinstance(endpoints, dict):
        endpoints = endpoints.get("endpoints") or endpoints.get("vector_search_endpoints") or endpoints.get("items") or []
    if not isinstance(endpoints, list):
        return None
    for item in endpoints:
        if not isinstance(item, dict):
            continue
        if item.get("name") == name:
            return item
    return None


def get_endpoint_id(endpoint):
    if not isinstance(endpoint, dict):
        return None
    return endpoint.get("endpoint_id") or endpoint.get("id") or (endpoint.get("endpoint") or {}).get("endpoint_id")


def main():
    parser = argparse.ArgumentParser(description="Assign Vector Search endpoint permissions to a service principal.")
    parser.add_argument("--host", required=True, help="Databricks workspace host (https://...)")
    parser.add_argument("--endpoint-name", required=True, help="Vector Search endpoint name")
    parser.add_argument("--service-principal-app-id", required=True, help="Service principal application (client) ID")
    parser.add_argument("--workspace-resource-id", required=True, help="Azure Databricks workspace resource ID")
    parser.add_argument("--permission-level", default="CAN_MANAGE", help="Permission level to grant")
    parser.add_argument("--skip-if-missing", action="store_true", help="Skip if endpoint is not found")
    args = parser.parse_args()

    host = normalize_host(args.host)
    token = get_token("2ff814a6-3304-4ab8-85cb-cd0e6f879c1d")

    headers = {
        "X-Databricks-Azure-Workspace-Resource-Id": args.workspace_resource_id,
    }
    try:
        headers["X-Databricks-Azure-SP-Management-Token"] = get_token("https://management.azure.com/")
    except FileNotFoundError:
        pass

    list_url = f"{host}/api/2.0/vector-search/endpoints"
    endpoints = request_json("GET", list_url, token, headers=headers)
    endpoint = resolve_endpoint(endpoints, args.endpoint_name)
    if endpoint is None:
        if args.skip_if_missing:
            print(f"Endpoint '{args.endpoint_name}' not found; skipping.")
            return 0
        raise RuntimeError(f"Endpoint '{args.endpoint_name}' not found.")

    endpoint_id = get_endpoint_id(endpoint)
    if not endpoint_id:
        raise RuntimeError(f"Could not resolve endpoint_id for '{args.endpoint_name}': {endpoint}")

    permissions_url = f"{host}/api/2.0/permissions/vector-search-endpoints/{endpoint_id}"
    payload = {
        "access_control_list": [
            {
                "service_principal_name": args.service_principal_app_id,
                "permission_level": args.permission_level,
            }
        ]
    }

    try:
        request_json("PATCH", permissions_url, token, headers=headers, payload=payload)
    except RuntimeError as exc:
        if "Databricks API error 404" in str(exc) or "Databricks API error 405" in str(exc):
            request_json("PUT", permissions_url, token, headers=headers, payload=payload)
        else:
            raise

    print(f"Granted {args.permission_level} on '{args.endpoint_name}' to {args.service_principal_app_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
