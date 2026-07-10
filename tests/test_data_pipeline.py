"""Tests for public-data parsing primitives."""

from __future__ import annotations

import hashlib
import io
import unittest
import zipfile

from scripts import download_binance_klines as downloader


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


if __name__ == "__main__":
    unittest.main()
