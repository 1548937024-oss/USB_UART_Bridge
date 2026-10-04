#!/usr/bin/env python3
"""Archive online datasheet PDFs and record local relative paths."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
METADATA_FIELDS = (
    "LCSC",
    "MPN",
    "Manufacturer",
    "Description",
    "Category",
    "Symbol",
    "Footprint",
    "Value",
    "Package",
    "Datasheet",
    "DatasheetRev",
    "DatasheetDate",
    "LocalDatasheet",
    "Lifecycle",
    "LCSC_URL",
    "Notes",
    "ReviewStatus",
)
SPECIAL_DATASHEET_URLS = {
    "C521963": (
        "https://atta.szlcsc.com/upload/public/pdf/source/20210810/"
        "E76C7C1824B0CB2A5B8963B3ABCE2DCE.pdf"
    ),
    "C7433196": (
        "https://atta.szlcsc.com/upload/public/pdf/source/20240424/"
        "1198EB55BDEE5099008B8334CDA766C6.pdf"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-csv", type=Path, required=True)
    parser.add_argument("--datasheets-dir", type=Path, required=True)
    parser.add_argument("--metadata-overrides", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--lcsc", nargs="+")
    return parser.parse_args()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def safe_filename(value: str) -> str:
    cleaned = INVALID_FILENAME.sub("_", value).strip().strip(".")
    return cleaned[:160] or "datasheet"


def is_pdf(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as handle:
        return handle.read(4096).lstrip().startswith(b"%PDF")


def normalized_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", "")
    )


def fallback_url(lcsc: str) -> str:
    if re.fullmatch(r"C\d+", lcsc, re.IGNORECASE):
        return f"https://www.lcsc.com/datasheet/{lcsc.upper()}.pdf"
    return ""


def download_pdf(url: str, destination: Path, retries: int = 3) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Referer": "https://www.szlcsc.com/",
        },
    )
    context = ssl.create_default_context()
    last_error: Exception | None = None
    for attempt in range(retries):
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with urllib.request.urlopen(request, timeout=60, context=context) as response:
                first = response.read(4096)
                if not first.lstrip().startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with temporary.open("wb") as handle:
                    handle.write(first)
                    shutil.copyfileobj(response, handle)
            temporary.replace(destination)
            return
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            OSError,
        ) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def load_metadata_overrides(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_metadata_overrides(
    path: Path,
    rows: list[dict[str, str]],
) -> None:
    normalized = []
    for row in rows:
        normalized.append(
            {
                field: clean(row.get(field))
                for field in METADATA_FIELDS
            }
        )
    normalized.sort(key=lambda row: row["LCSC"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)


def mark_override_issue(
    overrides: dict[str, dict[str, str]],
    lcsc: str,
    note: str,
) -> None:
    row = overrides.setdefault(lcsc, {"LCSC": lcsc})
    row["ReviewStatus"] = "CLASSIFIED_PARTIAL"
    existing = clean(row.get("Notes"))
    if note not in existing:
        row["Notes"] = f"{existing}; {note}".strip("; ")


def main() -> int:
    args = parse_args()
    parts_csv = args.parts_csv.resolve()
    datasheets_dir = args.datasheets_dir.resolve()
    overrides_path = args.metadata_overrides.resolve()
    report_path = args.report.resolve()

    with parts_csv.open(newline="", encoding="utf-8-sig") as handle:
        parts = list(csv.DictReader(handle))

    overrides = {
        clean(row.get("LCSC")).upper(): dict(row)
        for row in load_metadata_overrides(overrides_path)
        if clean(row.get("LCSC"))
    }
    requested = {
        value.strip().upper()
        for value in (args.lcsc or [])
        if value.strip()
    }
    cache_dir = Path(tempfile.mkdtemp(prefix="lcsc-datasheets-"))
    cache: dict[str, Path | None] = {}
    results: list[dict[str, str]] = []
    downloaded = 0
    copied = 0
    skipped = 0
    failed = 0
    missing_source = 0

    try:
        for index, row in enumerate(parts, start=1):
            lcsc = clean(row.get("LCSC")).upper()
            mpn = clean(row.get("MPN")) or lcsc
            if requested and lcsc not in requested:
                continue
            url = SPECIAL_DATASHEET_URLS.get(lcsc) or clean(row.get("Datasheet"))
            existing_local = clean(row.get("LocalDatasheet"))
            if existing_local:
                relative_path = existing_local.replace("\\", "/")
                target = (parts_csv.parent / relative_path).resolve()
            else:
                revision = clean(row.get("DatasheetRev"))
                stem = safe_filename(f"{mpn}_{revision}" if revision else mpn)
                relative_path = f"../datasheets/{lcsc}/{stem}.pdf"
                target = datasheets_dir / lcsc / f"{stem}.pdf"

            if not url:
                if is_pdf(target):
                    status = "existing-local"
                    skipped += 1
                else:
                    status = "missing-source"
                    missing_source += 1
                results.append(
                    {
                        "LCSC": lcsc,
                        "MPN": mpn,
                        "Status": status,
                        "Datasheet": url,
                        "LocalDatasheet": relative_path if is_pdf(target) else "",
                    }
                )
                print(
                    f"[{index}/{len(parts)}] {lcsc}: {status}",
                    flush=True,
                )
                continue

            if is_pdf(target) and not args.force:
                status = "existing-local"
                skipped += 1
                if lcsc not in overrides:
                    overrides[lcsc] = {"LCSC": lcsc}
                overrides[lcsc]["LocalDatasheet"] = relative_path
                results.append(
                    {
                        "LCSC": lcsc,
                        "MPN": mpn,
                        "Status": status,
                        "Datasheet": url,
                        "LocalDatasheet": relative_path,
                    }
                )
                print(
                    f"[{index}/{len(parts)}] {lcsc}: {status}",
                    flush=True,
                )
                continue

            cache_key = normalized_url(url)
            cached_path = cache.get(cache_key)
            status = "downloaded"
            if cached_path is None:
                cached_path = cache_dir / f"{safe_filename(cache_key)}.pdf"
                try:
                    download_pdf(url, cached_path)
                    downloaded += 1
                    cache[cache_key] = cached_path
                except RuntimeError as primary_error:
                    fallback = fallback_url(lcsc)
                    if fallback and normalized_url(fallback) != cache_key:
                        try:
                            download_pdf(fallback, cached_path)
                            downloaded += 1
                            cache[cache_key] = cached_path
                            status = "downloaded-fallback"
                        except RuntimeError as fallback_error:
                            failed += 1
                            mark_override_issue(
                                overrides,
                                lcsc,
                                "Preferred and fallback datasheet downloads failed.",
                            )
                            results.append(
                                {
                                    "LCSC": lcsc,
                                    "MPN": mpn,
                                    "Status": "failed",
                                    "Datasheet": url,
                                    "LocalDatasheet": "",
                                    "Error": f"{primary_error}; fallback: {fallback_error}",
                                }
                            )
                            print(
                                f"[{index}/{len(parts)}] {lcsc}: failed",
                                flush=True,
                            )
                            continue
                    else:
                        failed += 1
                        mark_override_issue(
                            overrides,
                            lcsc,
                            "Preferred datasheet download failed.",
                        )
                        results.append(
                            {
                                "LCSC": lcsc,
                                "MPN": mpn,
                                "Status": "failed",
                                "Datasheet": url,
                                "LocalDatasheet": "",
                                "Error": str(primary_error),
                            }
                        )
                        print(
                            f"[{index}/{len(parts)}] {lcsc}: failed",
                            flush=True,
                        )
                        continue
            else:
                status = f"copied-{cached_path.name}"
                copied += 1

            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".part")
            shutil.copyfile(cached_path, temporary)
            temporary.replace(target)
            if lcsc not in overrides:
                overrides[lcsc] = {"LCSC": lcsc}
            overrides[lcsc]["LocalDatasheet"] = relative_path
            results.append(
                {
                    "LCSC": lcsc,
                    "MPN": mpn,
                    "Status": status,
                    "Datasheet": url,
                    "LocalDatasheet": relative_path,
                }
            )
            print(
                f"[{index}/{len(parts)}] {lcsc}: {status}",
                flush=True,
            )
            if args.delay > 0:
                time.sleep(args.delay)
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

    write_metadata_overrides(overrides_path, list(overrides.values()))
    report = {
        "parts": len(parts),
        "downloaded": downloaded,
        "copied_from_cache": copied,
        "existing_or_skipped": skipped,
        "failed": failed,
        "missing_source": missing_source,
        "results": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Archived datasheets: downloaded={downloaded}, copied={copied}, "
        f"skipped={skipped}, failed={failed}, missing-source={missing_source}.",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
