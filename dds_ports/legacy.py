from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Iterable, Sequence, Union

from dagon import task

from . import crs
from .auto import read_package_json, read_library_jsons
from .port import PackageID
from .git import SimpleGitPort


class LegacyDDSGitPort(SimpleGitPort):
    def __init__(self, pkg_id: PackageID, url: str, tag: str) -> None:
        super().__init__(pkg_id.name, pkg_id, url, tag)

    def _fixup_crs(self, dirpath: Path) -> None:
        package_json = read_package_json(dirpath)
        deps = self._fixup_dependencies(package_json.get('depends', []))
        crs.write_crs_file(
            dirpath, {
                'name': package_json['name'],
                'version': package_json['version'],
                'pkg-version': 1,
                'libraries': list(self._fixup_libraries(dirpath, deps, package_json['name'])),
                'schema-version': 1,
            })

    @staticmethod
    def _fixup_libraries(dirpath: Path, deps: Sequence[crs.CRS_Dependency],
                         force_name: str) -> Iterable[crs.CRS_Library]:
        for libdir, lib in read_library_jsons(dirpath):
            relpath = libdir.relative_to(dirpath)
            lib_deps = deepcopy(deps)
            crs_lib: crs.CRS_Library = {
                'name': force_name,
                'path': str(relpath),
                'using': [],
                'test-using': [],
                'dependencies': list(lib_deps),
                'test-dependencies': [],
            }
            yield crs_lib

    @staticmethod
    def _fixup_dep_str(dep: str) -> crs.CRS_Dependency:
        s: str = dep
        mat = re.match(r'^[a-z0-9_.-]+', dep)
        assert mat, dep
        s = f'{dep} using ' + mat.group(0)
        return crs.convert_dep_str(s)

    def _fixup_dependencies(self, deps: Union[Sequence[str], dict[str, str]]) -> list[crs.CRS_Dependency]:
        if isinstance(deps, Sequence):
            return list(self._fixup_dep_str(dep) for dep in deps)
        return list(self._fixup_dep_str(key + mark) for key, mark in deps.items())

    async def _fixup(self, prepper: task.Task[Path]) -> Path:
        self._fixup_crs(await task.result_of(prepper))
        p: Path = await task.result_of(prepper)
        return p

    def make_prep_task(self) -> task.Task[Path]:
        prep = super().make_prep_task()
        return task.fn_task(f'{self.package_id}@fixup-legacy', lambda: self._fixup(prep), depends=[prep])

    def __repr__(self) -> str:
        return f'<LegacyDDSGitPort package={self.package_id} url=[{self._url}]>'
