"""Tests for public-data parsing primitives."""

from __future__ import annotations

import hashlib
import io
import unittest
import zipfile

from scripts import download_binance_klines as downloader
from scripts import download_binance_aggtrades as aggtrade_downloader


class DataPipelineTests(unittest.TestCase):
    def test_checksum_parser(self) -> None:
        digest = hashlib.sha256(b"archive").hexdigest()
        self.assertEqual(
            downloader.expected_checksum(f"{digest}  file.zip\n".encode("ascii")),
            digest,
        )

    def test_microsecond_archive_timestamp(self) -> None:
        row = (
            "1735689600000000,2600,2601,2599,2600.5,1,"
            "1735689899999999,2600.5,2,0.5,1300,0\n"
        )
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, mode="w") as archive:
            archive.writestr("sample.csv", row)
        frame = downloader.parse_archive(payload.getvalue())
        self.assertEqual(frame["time"].iloc[0].isoformat(), "2025-01-01T00:00:00+00:00")
        self.assertEqual(float(frame["close"].iloc[0]), 2600.5)

    def test_aggregate_trade_archive_accepts_duplicate_csv_entries(self) -> None:
        row = "1,2000.0,0.01,1,1,1704067200000,False,True\n"
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, mode="w") as archive:
            archive.writestr("PAXGUSDT-aggTrades-2024-01.csv", row)
            archive.writestr("nested/PAXGUSDT-aggTrades-2024-01.csv", row)
        frame = aggtrade_downloader.parse_archive(payload.getvalue())
        self.assertEqual(len(frame), 1)
        self.assertFalse(bool(frame["is_buyer_maker"].iloc[0]))
        self.assertEqual(frame["time"].iloc[0].isoformat(), "2024-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
