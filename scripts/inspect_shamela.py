"""Inspect the Shamela full database zip without downloading it (12.4 GB).

The organizers' reference file (page 15) lists the full database at
https://shamela.ws/page/download. The server supports HTTP range requests, so
this script reads only the zip's central directory (its file index) and prints
the archive layout: top-level folders, file counts and sizes, and the largest
small files that may hold the book catalogue. It downloads no book content.
"""
import io
import sqlite3
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://dev.shamela.ws/downloads/shamela-database-1448.zip"
VERBOSE = "--verbose" in sys.argv  # log every range request to stderr
MIN_INTERVAL_S = 3.0  # minimum gap between range requests (see _get_range)
READ_AHEAD = 8 * 1024 * 1024  # bytes fetched per request when zipfile reads small chunks
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "shamela"
CATALOGUE = "database/master.db"
TITLES = ("صحيح البخاري", "صحيح مسلم")


class HttpRangeFile(io.RawIOBase):
    """Read-only, seekable file over HTTP range requests (enough for zipfile)."""

    def __init__(self, url: str):
        self.url = url
        # No HEAD request: after a HEAD on the same session this server ignores Range
        # and starts sending the whole 12.4 GB file. The size comes from Content-Range.
        self.size = None
        self.pos = 0
        self.bytes_fetched = 0
        self.requests_made = 0
        self.last_request = 0.0
        self.buf = b""
        self.buf_start = 0
        self.size = int(self._get_range(0, 0)[1].split("/")[-1])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        n = min(n, self.size - self.pos)
        # Serve from the read-ahead buffer when possible; zipfile reads in small chunks
        # and each request costs MIN_INTERVAL_S.
        if not (self.buf_start <= self.pos and self.pos + n <= self.buf_start + len(self.buf)):
            end = min(self.pos + max(n, READ_AHEAD), self.size) - 1
            self.buf, _ = self._get_range(self.pos, end)
            self.buf_start = self.pos
        offset = self.pos - self.buf_start
        data = self.buf[offset:offset + n]
        self.pos += len(data)
        return data

    def _get_range(self, start: int, end: int) -> tuple[bytes, str]:
        """GET bytes start..end inclusive. Refuses any response that is not exactly that range."""
        # Back-to-back range requests get a full 200 response from this server (observed
        # 2026-10-03); requests spaced 3 s apart get proper 206 responses. Respect that.
        wait = MIN_INTERVAL_S - (time.monotonic() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.monotonic()
        started = time.monotonic()
        resp = requests.get(self.url, headers={"Range": f"bytes={start}-{end}"}, timeout=60, stream=True)
        expected = end - start + 1
        # Check before reading the body, so a server that ignores Range cannot
        # make us download the whole archive.
        if resp.status_code != 206 or int(resp.headers.get("Content-Length", -1)) != expected:
            resp.close()
            raise IOError(f"Expected 206 with {expected} bytes, got {resp.status_code}"
                          f" with Content-Length {resp.headers.get('Content-Length')}")
        data = resp.content
        self.bytes_fetched += len(data)
        self.requests_made += 1
        if VERBOSE:
            print(f"  [range] offset {start:,} length {len(data):,} in {time.monotonic() - started:.1f}s",
                  file=sys.stderr, flush=True)
        return data, resp.headers["Content-Range"]


def main() -> None:
    remote = HttpRangeFile(URL)
    print(f"Archive size: {remote.size:,} bytes")
    zf = zipfile.ZipFile(remote)
    infos = zf.infolist()
    print(f"Entries: {len(infos):,}")
    print(f"Fetched to read the index: {remote.bytes_fetched:,} bytes in {remote.requests_made} requests")

    # Layout by the first two path components.
    groups = defaultdict(lambda: [0, 0])
    exts = Counter()
    for info in infos:
        parts = info.filename.strip("/").split("/")
        key = "/".join(parts[:2]) if len(parts) > 2 else "/".join(parts[:1])
        groups[key][0] += 1
        groups[key][1] += info.file_size
        if not info.is_dir():
            exts[info.filename.rsplit(".", 1)[-1].lower() if "." in parts[-1] else "(none)"] += 1
    print("\nTop folders (first two levels): count, uncompressed size")
    for key, (count, size) in sorted(groups.items(), key=lambda kv: -kv[1][1])[:30]:
        print(f"  {count:>8,}  {size / 1e6:>10,.1f} MB  {key}")
    print("\nFile extensions:", dict(exts.most_common(15)))

    print("\nFiles directly under the first two levels (possible catalogues):")
    for info in infos:
        depth = info.filename.strip("/").count("/")
        if not info.is_dir() and depth <= 1:
            print(f"  {info.file_size:>14,}  {info.compress_size:>14,}  {info.filename}")

    print("\nSample of 15 deeper paths:")
    deep = [i for i in infos if not i.is_dir() and i.filename.count("/") >= 2]
    for info in deep[:: max(1, len(deep) // 15)][:15]:
        print(f"  {info.file_size:>14,}  {info.filename}")

    books = sorted((i for i in infos if i.filename.startswith("database/book/")), key=lambda i: -i.file_size)
    print("\nLargest 8 files under database/book/:")
    for info in books[:8]:
        print(f"  {info.file_size:>14,}  {info.filename}")
    print("\nSubfolders of database/store/:")
    store = defaultdict(lambda: [0, 0])
    for info in infos:
        parts = info.filename.split("/")
        if parts[:2] == ["database", "store"] and len(parts) > 3:
            store[parts[2]][0] += 1
            store[parts[2]][1] += info.file_size
    for name, (count, size) in sorted(store.items(), key=lambda kv: -kv[1][1]):
        print(f"  {count:>6,}  {size / 1e6:>10,.1f} MB  {name}")

    # Fetch only the catalogue (small) to find the two Sahihs.
    catalogue = RAW_DIR / "master.db"
    if not catalogue.exists():
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        catalogue.write_bytes(zf.read(CATALOGUE))
    print(f"\nTotal fetched so far: {remote.bytes_fetched:,} bytes in {remote.requests_made} requests")
    con = sqlite3.connect(catalogue)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"\n{CATALOGUE} tables: {tables}")
    for table in tables:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info('{table}')")]
        count = con.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
        print(f"  {table} ({count:,} rows): {cols}")
    for table in tables:
        cols = [r[1] for r in con.execute(f"PRAGMA table_info('{table}')")]
        name_cols = [c for c in cols if "name" in c.lower() or "title" in c.lower()]
        for col in name_cols:
            for title in TITLES:
                rows = con.execute(f"SELECT * FROM '{table}' WHERE \"{col}\" LIKE ?", (f"%{title}%",)).fetchall()
                if rows:
                    print(f"\n  {table}.{col} LIKE '%{title}%': {len(rows)} rows (first 12)")
                    for row in rows[:12]:
                        print("   ", dict(zip(cols, (str(v)[:120] if v is not None else None for v in row))))


if __name__ == "__main__":
    main()
