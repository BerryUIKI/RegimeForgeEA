"""Download verified Binance aggregate-trade archives and create order-flow bars."""

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


BASE_URL = "https://data.binance.vision/data/spot/monthly/aggTrades"
COLUMNS = [
    "aggregate_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "time",
    "is_buyer_maker",
    "is_best_match",
]


def fetch(url: str, attempts: int = 5) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "RegimeForgeEA/1.0"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def months(start: str, end: str) -> pd.PeriodIndex:
    return pd.period_range(pd.Period(start, freq="M"), pd.Period(end, freq="M"), freq="M")


def parse_archive(payload: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".csv")]
        if not names:
            raise ValueError("No CSV in aggregate-trade archive")
        with archive.open(min(names, key=len)) as source:
            frame = pd.read_csv(source, names=COLUMNS, header=None)
    frame["time"] = pd.to_datetime(frame["time"], unit="us" if frame["time"].iloc[0] >= 10**15 else "ms", utc=True)
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="raise")
    frame["is_buyer_maker"] = frame["is_buyer_maker"].astype(str).str.lower().eq("true")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="PAXGUSDT")
    parser.add_argument("--start", default="2021-01")
    parser.add_argument("--end", default="2025-12")
    parser.add_argument(
        "--bar-interval",
        default="5min",
        help="Pandas resampling interval for derived bars, such as 1min or 5min.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache/binance-aggtrades"))
    parser.add_argument(
        "--weekdays-only",
        action="store_true",
        help="Remove Saturday and Sunday UTC observations for a 24/5 XAUUSD proxy.",
    )
    args = parser.parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    manifest: list[dict[str, str]] = []
    missing_months: list[str] = []

    for month in months(args.start, args.end):
        filename = f"{args.symbol}-aggTrades-{month.strftime('%Y-%m')}.zip"
        url = f"{BASE_URL}/{args.symbol}/{filename}"
        archive_path = args.cache_dir / filename
        checksum_path = args.cache_dir / f"{filename}.CHECKSUM"
        try:
            checksum_text = checksum_path.read_bytes() if checksum_path.exists() else fetch(f"{url}.CHECKSUM")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                missing_months.append(str(month))
                print(f"missing {month}")
                continue
            raise
        expected = checksum_text.decode("ascii").split()[0].lower()
        archive = archive_path.read_bytes() if archive_path.exists() else fetch(url)
        actual = hashlib.sha256(archive).hexdigest()
        if actual != expected:
            if archive_path.exists():
                archive_path.unlink()
                archive = fetch(url)
                actual = hashlib.sha256(archive).hexdigest()
            if actual != expected:
                raise ValueError(f"Checksum mismatch for {filename}")
        archive_path.write_bytes(archive)
        checksum_path.write_bytes(checksum_text)
        frames.append(parse_archive(archive))
        manifest.append({"file": filename, "sha256": actual, "url": url})
        print(f"verified {filename}")

    if not frames:
        raise RuntimeError("No aggregate-trade archives were available")
    trades = pd.concat(frames, ignore_index=True).sort_values("time")
    trades["buy_taker_quantity"] = trades["quantity"].where(~trades["is_buyer_maker"], 0.0)
    trades["sell_taker_quantity"] = trades["quantity"].where(trades["is_buyer_maker"], 0.0)
    bars = trades.set_index("time").resample(args.bar_interval).agg(
        open=("price", "first"),
        high=("price", "max"),
        low=("price", "min"),
        close=("price", "last"),
        volume=("quantity", "sum"),
        buy_taker_quantity=("buy_taker_quantity", "sum"),
        sell_taker_quantity=("sell_taker_quantity", "sum"),
        trade_count=("quantity", "size"),
    )
    bars["total_taker_quantity"] = bars["buy_taker_quantity"] + bars["sell_taker_quantity"]
    bars["order_flow_imbalance"] = (
        (bars["buy_taker_quantity"] - bars["sell_taker_quantity"])
        / bars["total_taker_quantity"].replace(0.0, pd.NA)
    )
    bars = bars.dropna(subset=["open", "high", "low", "close", "order_flow_imbalance"])
    if args.weekdays_only:
        bars = bars.loc[bars.index.dayofweek < 5]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(args.output, index_label="time")
    args.output.with_suffix(".manifest.json").write_text(
        pd.Series(
            {
                "source": BASE_URL,
                "archives": manifest,
                "missing_months": missing_months,
                "bars": len(bars),
                "bar_interval": args.bar_interval,
                "weekdays_only": args.weekdays_only,
            }
        ).to_json(indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
