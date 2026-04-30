#!/usr/bin/env python3

# Copyright 2023-2026 Nils Knieling. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Fetch all predefined Google Cloud IAM roles and their permissions in parallel
via direct REST calls to the IAM API.

Replaces ``roles.sh`` + ``permissions.sh`` (which shelled out to ``gcloud``
once per role and were therefore very slow).

Authentication:
    The OAuth2 access token is obtained from ``gcloud`` (a single call to
    ``gcloud auth print-access-token`` at startup) or supplied explicitly via
    ``--token`` / the ``GCLOUD_TOKEN`` environment variable. No refresh is
    performed; a typical run completes well within the token lifetime.

Outputs (compatible with ``build.pl``):
    * roles.json - same shape as ``gcloud iam roles list --format=json``
    * role-permission-filter.json
    * permissions.csv - ``name;permissions`` with comma-separated permissions

Uses only the Python 3 standard library (no third-party dependencies).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

IAM_BASE = "https://iam.googleapis.com/v1"
ROLE_PERMISSION_FILTER_URL = (
    "https://docs.cloud.google.com/iam/json/role-permission-filter.json"
)
HTTP_TIMEOUT = 30  # seconds

# Roles to exclude from the permissions CSV (basic + legacy primitive roles).
SKIP_ROLES = {
    "roles/reader",
    "roles/writer",
    "roles/admin",
    "roles/owner",
    "roles/editor",
    "roles/viewer",
}


def get_token_from_gcloud() -> str:
    """Run ``gcloud auth print-access-token`` and return the token."""
    if shutil.which("gcloud") is None:
        raise RuntimeError(
            "gcloud not found in PATH. Install the Google Cloud SDK or "
            "pass a token via --token / GCLOUD_TOKEN."
        )
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"`gcloud auth print-access-token` failed (exit {exc.returncode}): "
            f"{exc.stderr.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("`gcloud auth print-access-token` timed out") from exc

    token = result.stdout.strip()
    if not token:
        raise RuntimeError("`gcloud auth print-access-token` returned an empty token")
    return token


def http_get_json(
    url: str,
    token: str,
    params: dict[str, Any] | None = None,
    *,
    max_attempts: int = 6,
) -> dict[str, Any]:
    """GET a URL with bearer auth, decode JSON, retry on 429 / 5xx / transient errors.

    Uses ``urllib.request`` from the standard library (no third-party deps).
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    backoff = 1.0
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "gcloud-iam-permissions/1.0 (+stdlib-urllib)",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                # 2xx responses always reach this branch.
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(
                f"GET {url} failed: HTTP {status} {exc.reason}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            # DNS errors, connection resets, timeouts, etc.
            if attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc
        except TimeoutError as exc:
            if attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(f"GET {url} timed out") from exc

    raise RuntimeError(f"GET {url} exhausted retries")


def list_all_roles(token: str) -> list[dict[str, Any]]:
    """List every predefined role (paginated)."""
    roles: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        data = http_get_json(f"{IAM_BASE}/roles", token, params=params)
        roles.extend(data.get("roles", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    roles.sort(key=lambda r: r.get("name", ""))
    return roles


def describe_role(token: str, name: str) -> dict[str, Any]:
    """Get a single role; ``roles.get`` always returns ``includedPermissions``.

    Note: unlike ``roles.list``, the ``roles.get`` endpoint does not accept a
    ``view`` query parameter — passing one yields HTTP 400.
    """
    return http_get_json(f"{IAM_BASE}/{name}", token)


def download_file(url: str, dest: str, *, max_attempts: int = 5) -> int:
    """Download ``url`` to ``dest`` (binary), with retry on transient errors.

    Returns the number of bytes written. No auth headers are sent.
    """
    backoff = 1.0
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, */*",
                "User-Agent": "gcloud-iam-permissions/1.0 (+stdlib-urllib)",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            return len(data)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < max_attempts:
                time.sleep(backoff + (0.1 * attempt))
                backoff = min(backoff * 2, 30.0)
                continue
            raise RuntimeError(f"Download {url} failed: {exc}") from exc
    raise RuntimeError(f"Download {url} exhausted retries")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workers",
        type=int,
        default=32,
        help="Number of concurrent threads (default: 32).",
    )
    parser.add_argument(
        "--token",
        default=None,
        help=(
            "OAuth2 access token. If omitted, falls back to the GCLOUD_TOKEN "
            "environment variable, then to `gcloud auth print-access-token`."
        ),
    )
    parser.add_argument(
        "--roles-json",
        default="roles.json",
        help="Output path for the roles list JSON (default: roles.json).",
    )
    parser.add_argument(
        "--roles-txt",
        default="roles.txt",
        help=(
            "Output path for the sorted role-name list, one per line, each "
            "name wrapped in double quotes (default: roles.txt)."
        ),
    )
    parser.add_argument(
        "--permissions-csv",
        default="permissions.csv",
        help="Output path for the permissions CSV (default: permissions.csv).",
    )
    parser.add_argument(
        "--filter-json",
        default="role-permission-filter.json",
        help=(
            "Output path for the role-permission filter JSON downloaded from "
            "docs.cloud.google.com (default: role-permission-filter.json)."
        ),
    )
    parser.add_argument(
        "--skip-filter-download",
        action="store_true",
        help="Do not download role-permission-filter.json.",
    )
    args = parser.parse_args()

    # Resolve token: --token > $GCLOUD_TOKEN > `gcloud auth print-access-token`.
    token = args.token or os.environ.get("GCLOUD_TOKEN")
    if token:
        token = token.strip()
        print("Using access token from CLI/env.", flush=True)
    else:
        print("Fetching access token via `gcloud auth print-access-token`...", flush=True)
        token = get_token_from_gcloud()

    if not args.skip_filter_download:
        print(
            f"Get role permission filter from {ROLE_PERMISSION_FILTER_URL}...",
            flush=True,
        )
        size = download_file(ROLE_PERMISSION_FILTER_URL, args.filter_json)
        print(f"  -> {size} bytes written to {args.filter_json}", flush=True)

    print("Get roles... Please wait...", flush=True)
    roles = list_all_roles(token)
    with open(args.roles_json, "w", encoding="utf-8") as f:
        json.dump(roles, f, indent=2, ensure_ascii=False)
    print(f"  -> {len(roles)} roles written to {args.roles_json}", flush=True)

    # Sorted, quoted role-name list (matches the output of the previous
    # `jq '.[].name' roles.json | sort -u` pipeline in permissions.sh).
    sorted_names = sorted({r["name"] for r in roles if r.get("name")})
    with open(args.roles_txt, "w", encoding="utf-8") as f:
        for name in sorted_names:
            f.write(f'"{name}"\n')
    print(f"  -> {len(sorted_names)} role names written to {args.roles_txt}", flush=True)

    targets = [r["name"] for r in roles if r.get("name") not in SKIP_ROLES]
    print(
        f"Get permissions for {len(targets)} roles using {args.workers} workers...",
        flush=True,
    )

    results: dict[str, list[str]] = {}
    errors: list[tuple[str, str]] = []
    completed = 0
    total = len(targets)
    progress_lock = Lock()

    def worker(role_name: str) -> tuple[str, list[str]]:
        role = describe_role(token, role_name)
        return role_name, role.get("includedPermissions", []) or []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, name): name for name in targets}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                role_name, perms = fut.result()
                results[role_name] = perms
            except Exception as exc:  # noqa: BLE001
                errors.append((name, str(exc)))
            with progress_lock:
                completed += 1
                if completed % 100 == 0 or completed == total:
                    print(f"  [{completed}/{total}]", flush=True)

    # Write CSV in deterministic (sorted) order so diffs stay clean.
    # Build the full payload first, join with '\n', and write in one go so
    # there is no trailing newline after the last row. Role names and
    # permission identifiers contain no ';', ',', '"' or newlines, so plain
    # string concatenation is safe (no need for the csv module).
    lines = ["name;permissions"]
    for name in sorted(results):
        lines.append(f"{name};{','.join(results[name])}")
    with open(args.permissions_csv, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
    print(f"  -> {args.permissions_csv} written", flush=True)

    if errors:
        print(f"\n{len(errors)} role(s) failed:", file=sys.stderr)
        for name, msg in errors[:20]:
            print(f"  - {name}: {msg}", file=sys.stderr)
        return 9

    # Quick sanity checks (mirror the original bash script).
    print("Quick test", flush=True)
    required = ("roles/compute.admin", "roles/bigquery.admin", "roles/billing.admin")
    missing = [r for r in required if r not in results or not results[r]]
    if missing:
        print(f"FAIL: missing/empty roles: {missing}", file=sys.stderr)
        return 9
    for r in required:
        print(f"  ok: {r} ({len(results[r])} permissions)")

    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
