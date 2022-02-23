import itertools
from pathlib import Path, PurePosixPath
import tempfile
from semver import VersionInfo
import zipfile
from typing import NamedTuple, Sequence
import aiohttp.client

from dagon import task
import dagon.ui

from dds_ports import port, util, crs


class SQLite3VersionGroup(NamedTuple):
    year: int
    major: int
    minor: int
    patches: Sequence[int]


VERSION_GROUPS = [
    SQLite3VersionGroup(2021, 3, 35, [0, 1, 2, 3, 4]),
    SQLite3VersionGroup(2021, 3, 34, [1]),
    SQLite3VersionGroup(2020, 3, 34, [0]),
    SQLite3VersionGroup(2020, 3, 33, [0]),
    SQLite3VersionGroup(2020, 3, 32, [0, 1, 2, 3]),
    SQLite3VersionGroup(2020, 3, 31, [0, 1]),
    SQLite3VersionGroup(2019, 3, 30, [0, 1]),
    SQLite3VersionGroup(2019, 3, 29, [0]),
    SQLite3VersionGroup(2019, 3, 28, [0]),
    SQLite3VersionGroup(2019, 3, 27, [0, 1, 2]),
    SQLite3VersionGroup(2018, 3, 26, [0]),
    SQLite3VersionGroup(2018, 3, 25, [0]),
    SQLite3VersionGroup(2018, 3, 24, [0]),
    SQLite3VersionGroup(2018, 3, 23, [0, 1]),
    SQLite3VersionGroup(2018, 3, 22, [0]),
    SQLite3VersionGroup(2017, 3, 21, [0]),
    SQLite3VersionGroup(2017, 3, 20, [0, 1]),
    SQLite3VersionGroup(2017, 3, 19, [0, 1, 2, 3]),
    # SQLite3VersionGroup(2017, 3, 18, [0, 1, 2]),
    # SQLite3VersionGroup(2017, 3, 17, [0]),
    # SQLite3VersionGroup(2017, 3, 16, [0, 1, 2]),
    # SQLite3VersionGroup(2016, 3, 15, [0, 1, 2]),
    # SQLite3VersionGroup(2016, 3, 14, [0, 1, 2]),
    # SQLite3VersionGroup(2016, 3, 13, [0]),
    # SQLite3VersionGroup(2016, 3, 12, [0, 1, 2]),
    # SQLite3VersionGroup(2016, 3, 11, [0, 1]),
    # SQLite3VersionGroup(2016, 3, 10, [0, 1, 2]),
]

CONFIGS = [
    ('SQLITE_THREADSAFE', 2),
    ('SQLITE_OMIT_LOAD_EXTENSION', 1),
    ('SQLITE_OMIT_DEPRECATED', 1),
    ('SQLITE_DEFAULT_MEMSTATUS', 0),
    ('SQLITE_DQS', 0),
]

tmpl = r'''
#ifndef {macro}
#define {macro} {default}
#endif
'''

DEFAULT_CONFIG = ''.join(tmpl.format(macro=m, default=d) for m, d in CONFIGS)

SRC_PREFIX = r'''
/**
 * The contents of this preamble are not part of the main sqlite3 distribution,
 * and are inserted as part of the dds port for sqlite3.
 */

#if defined(__has_include)
#  if __has_include(<sqlite3.tweaks.h>)
#    include <sqlite3.tweaks.h>
#  endif
#endif

''' + DEFAULT_CONFIG + r'''

/** End of dds-inserted configuration preamble */

'''


async def prep_sqlite3_dir(destdir: Path, url: str, version: VersionInfo) -> None:
    topdir = PurePosixPath(url).with_suffix('').name
    with util.temporary_directory(f'sqlite3-{version}') as tmpdir:
        zip_dest = tmpdir / 'archive.zip'
        dagon.ui.status(f'Downloading SQLite3 archive for {version}')
        async with aiohttp.client.ClientSession() as sess:
            resp = await sess.get(url)
            resp.raise_for_status()
            with zip_dest.open('wb') as ofd:
                while 1:
                    buf = await resp.content.read(1024)
                    if not buf:
                        break
                    ofd.write(buf)

        with zipfile.ZipFile(zip_dest) as zf:
            destdir.joinpath('src/sqlite3').mkdir(exist_ok=True, parents=True)
            for fname in ('sqlite3.h', 'sqlite3.c', 'sqlite3ext.h'):
                with zf.open(f'{topdir}/{fname}') as sf:
                    content = sf.read()
                    content = SRC_PREFIX.encode() + content
                    destdir.joinpath('src/sqlite3', fname).write_bytes(content)


class SQLite3Port:
    def __init__(self, year: int, version: VersionInfo) -> None:
        self.year = year
        self.version = version
        self.package_id = port.PackageID('sqlite3', version, 1)

    async def _prep_sd(self) -> Path:
        ver = self.version
        url = f'https://sqlite.org/{self.year}/sqlite-amalgamation-{ver.major}{ver.minor:0>2}{ver.patch:0>2}00.zip'
        tmpdir = Path(tempfile.mkdtemp(suffix=f'-dds-ports-sqlite3-{ver}'))

        await prep_sqlite3_dir(tmpdir, url, ver)
        crs.write_crs_file(
            tmpdir,
            {
                'name': 'sqlite3',
                'version': str(self.version),
                'pkg-version': 1,
                'libraries': [{
                    'name': 'sqlite3',
                    'path': '.',
                    'using': [],
                    'dependencies': [],
                }],
                'schema-version': 1,
            },
        )
        return tmpdir

    def make_prep_task(self) -> task.Task[Path]:
        return task.fn_task(str(self.package_id), self._prep_sd)


async def all_ports() -> port.PortIter:
    quads = itertools.chain.from_iterable((
        (grp.year, grp.major, grp.minor, patch)  #
        for patch in grp.patches  #
    ) for grp in VERSION_GROUPS)
    return (
        SQLite3Port(year, VersionInfo(major, minor, patch))  #
        for year, major, minor, patch in quads  #
    )
