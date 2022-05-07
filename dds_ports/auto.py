from __future__ import annotations

from copy import deepcopy
import itertools
from asyncio import Semaphore
from pathlib import Path
from typing import Callable, Iterable, Sequence, Optional, NamedTuple, Awaitable, cast
from typing_extensions import TypedDict
import json5

import dagon.ui
import dagon.fs
import dagon.proc
import dagon.pool
from dagon import task
from semver import VersionInfo

from dds_ports.port import Port, PackageID
from dds_ports import git, github, util, crs

PackageJSON = TypedDict('PackageJSON', {
    'name': str,
    'namespace': str,
    'version': str,
    'depends': Sequence[str],
})

LibraryJSON = TypedDict('LibraryJSON', {
    'name': str,
    'uses': Sequence[str],
})

FSTransformFn = Callable[[Path], Awaitable[None]]

BUILD_SEMAPHORE = Semaphore(1)


def read_package_json(dirpath: Path) -> PackageJSON:
    for fname in ('package.json', 'package.jsonc', 'package.json5'):
        cand = dirpath / fname
        if not cand.is_file():
            continue
        return cast(PackageJSON, json5.loads(cand.read_text()))
    raise RuntimeError(f'No package.json[c5] file in [{dirpath}]')


def read_library_jsons(dirpath: Path) -> Iterable[tuple[Path, LibraryJSON]]:
    lib_fnames = ('library.json', 'library.jsonc', 'library.json5')
    for fname in lib_fnames:
        cand = dirpath / fname
        if not cand.is_file():
            continue
        yield dirpath, cast(LibraryJSON, json5.loads(cand.read_text()))

    lib_dir = dirpath / 'libs'
    if not lib_dir.is_dir():
        return
    for sublib, fname in itertools.product(lib_dir.iterdir(), lib_fnames):
        cand = sublib / fname
        if not cand.is_file():
            continue
        yield sublib, cast(LibraryJSON, json5.loads(cand.read_text()))


class SimpleGitHubAdaptingPort(NamedTuple):
    package_id: PackageID
    owner: str
    repo: str
    tag: str
    crs_json: crs.CRS_JSON
    fs_transform: FSTransformFn
    try_build: bool

    async def _prep_crs(self, cloner: task.Task[Path]) -> Path:
        clone: Path = await task.result_of(cloner)
        dagon.ui.status(f'Generating sdist for {self.package_id}')
        full_crs_json = deepcopy(self.crs_json)
        full_crs_json['name'] = self.package_id.name
        full_crs_json['version'] = str(self.package_id.version)
        full_crs_json['pkg-version'] = self.package_id.revision
        crs.write_crs_file(clone, full_crs_json)
        await self.fs_transform(clone)
        return clone

    def make_prep_task(self) -> task.Task[Path]:
        simple = git.SimpleGitPort(
            f'gh/{self.owner}/{self.repo}',
            self.package_id,
            github.gh_repo_url(self.owner, self.repo),
            self.tag,
        ).make_prep_task()
        return task.fn_task(f'{self.package_id}@fixup', lambda: self._prep_crs(simple), depends=[simple])


def _version_in_range(ver: VersionInfo, min_: VersionInfo, max_: VersionInfo) -> bool:
    if ver < min_:
        return False
    if ver >= max_:
        return False
    return True


def _tag_as_version(tag: str, owner: str, repo: str) -> VersionInfo | None:
    ver = util.tag_as_version(tag)
    if ver is None:
        print(f'Skipping non-version tag "{tag}" in {owner}/{repo}')
    return ver


async def get_repo_ports(owner: str, repo: str, *, min_version: VersionInfo, max_version: VersionInfo,
                         crs_json: crs.CRS_JSON, fs_transform: FSTransformFn, try_build: bool) -> Iterable[Port]:
    tags = list(await github.get_repo_tags(owner, repo))
    tagged_versions = list((tag, _tag_as_version(tag, owner, repo)) for tag in tags)
    return (  #
        SimpleGitHubAdaptingPort(
            package_id=PackageID(crs_json['name'], version, revision=1),
            owner=owner,
            repo=repo,
            tag=tag,
            crs_json=crs_json,
            fs_transform=fs_transform,
            try_build=try_build,
        )  #
        for tag, version in tagged_versions  #
        if version is not None and _version_in_range(version, min_version, max_version)  #
    )


async def _null_transform(_p: Path) -> None:
    pass


async def enumerate_simple_github(
    *,
    owner: str,
    repo: str,
    min_version: VersionInfo = VersionInfo(0),
    max_version: VersionInfo = VersionInfo(99999999),
    package_name: Optional[str] = None,
    library_name: Optional[str] = None,
    depends: Optional[Sequence[str]] = None,
    fs_transform: Optional[FSTransformFn] = None,
    pkg_version: int = 1,
    try_build: bool = True,
) -> Iterable[Port]:
    return await get_repo_ports(
        owner,
        repo,
        min_version=min_version,
        max_version=max_version,
        crs_json={
            'name':
            package_name or repo,
            'pkg-version':
            pkg_version,
            'version':
            '[placeholder]',
            'schema-version':
            1,
            'libraries': [{
                'path': '.',
                'name': library_name or repo,
                'using': [],
                'test-using': [],
                'dependencies': [crs.convert_dep_str(d) for d in (depends or [])],
                'test-dependencies': [],
            }],
        },
        fs_transform=fs_transform or _null_transform,
        try_build=try_build,
    )
