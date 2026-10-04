# Bundled official source file

`kfgqpc_hafs_v30.zip` is the unmodified file published by the King Fahd Glorious Quran
Printing Complex on its developer platform:

- Source page: https://qurancomplex.gov.sa/quran-dev/ ("الخط الحاسوبي يونيكود (رواية حفص)", version 15.0)
- Official URL: https://download.qurancomplex.gov.sa/resources_dev/kfgqpc_hafs_v30.zip
- SHA-256 (published by the Complex, and of this file): `227E6B1564D980F2BD09C2C35EBFB0330AC268C79A7C247CD1AB665BC635F245`
- Downloaded: 2026-10-03

**Why it is here:** the Complex's download server is not reachable from our host
(connection timed out from Render, Frankfurt, on 2026-10-04). `scripts/ingest.py` always
tries the official URL first and uses this copy only if that fails. Either way the file is
accepted only if its SHA-256 matches the published value, so it is byte-for-byte the
official file. It is not a mirror or a different dataset.

**Rights:** the content belongs to the King Fahd Complex. The developer platform publishes
these files for developers; we found no explicit license (see SOURCES.md). This copy is
included unmodified, with credit, only so the application can be built.
