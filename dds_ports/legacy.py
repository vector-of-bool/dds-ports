from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import AsyncIterator, Iterable, Sequence, Union
from contextlib import asynccontextmanager

from . import crs
from .auto import read_package_json, read_library_jsons
from .port import PackageID
from .git import SimpleGitPort


def _filter_dep_usage(dep: crs.CRS_Dependency, use: str) -> bool:
    dname = dep['name']
    return {
        'neo/fun': dname == 'neo-fun',
        'sqlite3/sqlite3': dname == 'sqlite3',
        'neo/concepts': dname == 'neo-concepts',
        'neo/buffer': dname == 'neo-buffer',
        'zlib/zlib': dname == 'zlib',
    }[use]


class LegacyDDSGitPort(SimpleGitPort):
    def __init__(self, pkg_id: PackageID, url: str, tag: str) -> None:
        super().__init__(pkg_id, url, tag)

    @asynccontextmanager
    async def prepare_sdist(self) -> AsyncIterator[Path]:
        async with super().prepare_sdist() as clone:
            self._fixup_crs(clone)
            yield clone

    def _fixup_crs(self, dirpath: Path) -> None:
        package_json = read_package_json(dirpath)
        deps = self._fixup_dependencies(package_json.get('depends', []))
        crs.write_crs_file(
            dirpath, {
                'name': package_json['name'],
                'version': package_json['version'],
                'meta_version': 1,
                'namespace': package_json['namespace'],
                'libraries': list(self._fixup_libraries(dirpath, deps)),
                'crs_version': 1,
            })

    def _fixup_libraries(self, dirpath: Path, deps: Sequence[crs.CRS_Dependency]) -> Iterable[crs.CRS_Library]:
        for libdir, lib in read_library_jsons(dirpath):
            relpath = libdir.relative_to(dirpath)
            lib_deps = deepcopy(deps)
            for d in lib_deps:
                d['uses'] = [u for u in lib.get('uses', []) if _filter_dep_usage(d, u)]
            crs_lib: crs.CRS_Library = {
                'name': lib['name'],
                'path': str(relpath),
                'uses': [],
                'depends': list(lib_deps),
            }
            yield crs_lib

    def _fixup_dependencies(self, deps: Union[Sequence[str], dict[str, str]]) -> list[crs.CRS_Dependency]:
        print(f'Fixup deps for {self.package_id}')
        if isinstance(deps, Sequence):
            return list(crs.convert_dep_str(dep) for dep in deps)
        else:
            return list(crs.convert_dep_str(key + mark) for key, mark in deps.items())

    def __repr__(self) -> str:
        return f'<LegacyDDSGitPort package={self.package_id} url=[{self._url}]>'
