"""Download and verify public monthly kline archives from Binance Data Vision."""

from __future__ import annotations

import argparse
import hashlib
import io
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd


BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"
KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trade_count",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]


def month_range(start: str, end: str) -> pd.PeriodIndex:
    first = pd.Period(start, freq="M")
    last = pd.Period(end, freq="M")
    if last < first:
        raise ValueError("end month must not precede start month")
    return pd.period_range(first, last, freq="M")


def fetch(url: str, attempts: int = 5) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RegimeForgeEA/1.0 public-research-downloader"},
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            delay = 2 ** (attempt - 1)
            print(f"retrying {url} in {delay}s ({attempt}/{attempts})")
            time.sleep(delay)
    raise RuntimeError("unreachable")


def expected_checksum(payload: bytes) -> str:
    text = payload.decode("ascii").strip()
    checksum = text.split()[0].lower()
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise ValueError("Invalid SHA-256 checksum response")
    return checksum


def timestamp_unit(value: int) -> str:
    return "us" if abs(value) >= 10**15 else "ms"


def parse_archive(payload: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"Expected one CSV in archive, found {len(members)}")
        with archive.open(members[0]) as source:
            frame = pd.read_csv(source, header=None, names=KLINE_COLUMNS)

    if frame.empty:
        return frame
    unit = timestamp_unit(int(frame["open_time"].iloc[0]))
    frame["time"] = pd.to_datetime(frame["open_time"], unit=unit, utc=True)
    numeric = ["open", "high", "low", "close", "volume", "quote_volume", "trade_count"]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


def download_month(
    symbol: str,
    interval: str,
    month: pd.Period,
    cache_dir: Path,
) -> tuple[pd.DataFrame, dict[str, str]]:
    stem = f"{symbol}-{interval}-{month.strftime('%Y-%m')}.zip"
    url = f"{BASE_URL}/{symbol}/{interval}/{stem}"
    checksum_path = cache_dir / f"{stem}.CHECKSUM"
    checksum_payload = (
        checksum_path.read_bytes()
        if checksum_path.exists()
        else fetch(f"{url}.CHECKSUM")
    )
    checksum = expected_checksum(checksum_payload)
    cache_path = cache_dir / stem
    archive = cache_path.read_bytes() if cache_path.exists() else fetch(url)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != checksum:
        if cache_path.exists():
            print(f"discarding invalid cache file {cache_path}")
            cache_path.unlink()
            archive = fetch(url)
            actual = hashlib.sha256(archive).hexdigest()
        if actual != checksum:
            raise ValueError(f"Checksum mismatch for {stem}: {actual} != {checksum}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not cache_path.exists():
        cache_path.write_bytes(archive)
    if not checksum_path.exists():
        checksum_path.write_bytes(checksum_payload)
    print(f"verified {stem} sha256={actual}")
    return parse_archive(archive), {"file": stem, "sha256": actual, "url": url}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="PAXGUSDT")
    parser.add_argument("--interval", default="5m")
    parser.add_argument("--start", default="2021-01")
    parser.add_argument("--end", default="2025-12")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache/binance"))
    parser.add_argument(
        "--manifest-output",
        type=Path,
        help="Optional tracked copy of the data-quality and checksum manifest.",
    )
    parser.add_argument(
        "--weekdays-only",
        action="store_true",
        help="Remove Saturday and Sunday UTC bars for a closer 24/5 proxy.",
    )
    args = parser.parse_args()

    frames: list[pd.DataFrame] = []
    archives: list[dict[str, str]] = []
    missing: list[str] = []
    for month in month_range(args.start, args.end):
        try:
            frame, archive = download_month(
                args.symbol.upper(),
                args.interval,
                month,
                args.cache_dir,
            )
            frames.append(frame)
            archives.append(archive)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                missing.append(str(month))
                print(f"missing {month}")
                continue
            raise

    if not frames:
        raise RuntimeError("No archives were downloaded")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("time").drop_duplicates("time", keep="last")
    if args.weekdays_only:
        combined = combined.loc[combined["time"].dt.dayofweek < 5]

    output = combined[
        ["time", "open", "high", "low", "close", "volume", "quote_volume", "trade_count"]
    ].copy()
    output["spread"] = 35.0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")

    gaps = output["time"].diff().dropna()
    expected = pd.Timedelta(minutes=5)
    metadata = {
        "symbol": args.symbol.upper(),
        "interval": args.interval,
        "requested_start": args.start,
        "requested_end": args.end,
        "first_bar": output["time"].iloc[0].isoformat(),
        "last_bar": output["time"].iloc[-1].isoformat(),
        "bars": len(output),
        "weekdays_only": args.weekdays_only,
        "missing_months": missing,
        "duplicate_timestamps": int(output["time"].duplicated().sum()),
        "non_positive_prices": int((output[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        "gaps_over_five_minutes": int((gaps > expected).sum()),
        "source": BASE_URL,
        "archives": archives,
    }
    metadata_path = args.output.with_suffix(".metadata.json")
    metadata_json = pd.Series(metadata).to_json(indent=2, force_ascii=False)
    metadata_path.write_text(metadata_json, encoding="utf-8")
    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(metadata_json, encoding="utf-8")
    print(metadata_json)


if __name__ == "__main__":
    main()
