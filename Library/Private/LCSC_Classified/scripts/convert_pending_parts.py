#!/usr/bin/env python3
"""Convert pending LCSC parts into their classified KiCad symbol and footprint libraries."""

from __future__ import annotations

import argparse
import csv
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
EASYEDA_HOME_URL = "https://lceda.cn/"
EASYEDA_COMPONENT_URL = "https://lceda.cn/api/products/{lcsc_id}/components"
REQUEST_INTERVAL_SECONDS = 2.0


def read_json(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-index", type=Path, required=True)
    parser.add_argument("--library-root", type=Path, required=True)
    parser.add_argument("--easyeda-package", type=Path, required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.cwd() / ".easyeda_cache",
    )
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--retry-not-found", action="store_true")
    return parser.parse_args()


def build_easyeda_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    request = urllib.request.Request(
        EASYEDA_HOME_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with opener.open(request, timeout=30):
        pass
    return opener


def fetch_component_data(
    lcsc: str,
    opener: urllib.request.OpenerDirector,
    cache_dir: Path,
) -> tuple[bool, str]:
    cache_path = cache_dir / f"{lcsc}.json"
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = {}
        if isinstance(cached, dict) and cached.get("success") is not False:
            return True, "cached"

    request = urllib.request.Request(
        EASYEDA_COMPONENT_URL.format(lcsc_id=lcsc),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://lceda.cn/editor",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    try:
        with opener.open(request, timeout=30) as response:
            raw_data = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw_data)
    except urllib.error.HTTPError as error:
        if error.code == 403:
            return False, "rate_limited"
        if error.code == 404:
            return False, "not_found"
        return False, "failed"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False, "failed"

    if not isinstance(payload, dict) or payload.get("success") is False:
        if payload.get("code") == 404:
            return False, "not_found"
        return False, "failed"

    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_suffix(".json.tmp")
    temporary_path.write_text(raw_data, encoding="utf-8")
    temporary_path.replace(cache_path)
    return True, "fetched"


def convert_part(
    lcsc: str,
    category: str,
    library_root: Path,
    easyeda_package: Path,
    cache_dir: Path,
    opener: urllib.request.OpenerDirector,
) -> tuple[bool, str]:
    cache_ready, cache_status = fetch_component_data(lcsc, opener, cache_dir)
    if not cache_ready:
        return False, cache_status

    category_dir = library_root / category
    category_dir.mkdir(parents=True, exist_ok=True)
    output_base = category_dir / category

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(easyeda_package)
    command = [
        sys.executable,
        "-m",
        "easyeda2kicad",
        "--lcsc_id",
        lcsc,
        "--symbol",
        "--footprint",
        "--use-cache",
        "--overwrite",
        "--output",
        str(output_base),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )
    output = f"{completed.stdout}\n{completed.stderr}"

    if re.search(r"HTTP Error 403", output):
        return False, "rate_limited"
    if re.search(r"HTTP Error 404", output):
        return False, "not_found"
    if "Failed to fetch data from EasyEDA API" in output:
        return False, "failed"
    if "Created Kicad symbol" in output and "Created Kicad footprint" in output:
        return True, "converted"
    return False, "failed"


def main() -> int:
    args = parse_args()
    index_path = args.library_index.resolve()
    library_root = args.library_root.resolve()
    easyeda_package = args.easyeda_package.resolve()
    cache_dir = args.cache_dir.resolve()
    state_path = args.state_file.resolve()

    state = read_json(state_path)
    with index_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    pending = []
    for row in rows:
        lcsc = (row.get("LCSC") or "").strip().upper()
        category = (row.get("LibraryCategory") or "").strip()
        if not lcsc or not category:
            continue
        if row.get("ConversionStatus") == "CONVERTED":
            continue
        previous_status = state.get(lcsc)
        if previous_status == "converted":
            continue
        if previous_status == "not_found" and not args.retry_not_found:
            continue
        if previous_status in {"failed", "rate_limited"} and not args.retry_failed:
            continue
        pending.append((lcsc, category))

    if args.limit is not None:
        pending = pending[: args.limit]

    successes = 0
    failures = 0
    opener = build_easyeda_opener() if pending else None

    for index, (lcsc, category) in enumerate(pending, start=1):
        if opener is None:
            raise RuntimeError("EasyEDA session was not initialized")
        ok, status = convert_part(
            lcsc,
            category,
            library_root,
            easyeda_package,
            cache_dir,
            opener,
        )
        state[lcsc] = status
        write_json(state_path, state)
        if ok:
            successes += 1
        else:
            failures += 1
        print(
            f"[{index}/{len(pending)}] {lcsc} -> {category}: {status}",
            flush=True,
        )
        if status == "rate_limited":
            print("EasyEDA rate limit reached; stopping this run.", flush=True)
            break
        time.sleep(REQUEST_INTERVAL_SECONDS)

    write_json(state_path, state)
    print(f"Converted {successes}; failed or unavailable {failures}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
