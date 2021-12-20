from __future__ import annotations

from copy import deepcopy
import itertools
from asyncio import Semaphore
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Iterable, Sequence, Optional, NamedTuple, AsyncIterator, Awaitable, cast
from typing_extensions import TypedDict
import json5

from semver import VersionInfo, max_ver

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

    @asynccontextmanager
    async def prepare_sdist(self) -> AsyncIterator[Path]:
        gh_port = git.SimpleGitPort(self.package_id, f'https://github.com/{self.owner}/{self.repo}.git', self.tag)
        async with gh_port.prepare_sdist() as clone:
            full_crs_json = deepcopy(self.crs_json)
            full_crs_json['name'] = self.package_id.name
            full_crs_json['version'] = str(self.package_id.version)
            full_crs_json['meta_version'] = self.package_id.meta_version
            crs.write_crs_file(clone, full_crs_json)
            await self.fs_transform(clone)
            if 0 and self.try_build:
                async with BUILD_SEMAPHORE:
                    print(f'Attempting a build of {self.package_id}...')
                    await util.run_process(
                        ['./dds', 'build', '--no-tests', f'--project={clone}', f'--out={clone/"_build"}'])
            yield clone


async def get_repo_ports(owner: str, repo: str, *, min_version: VersionInfo, max_version: VersionInfo,
                         crs_json: crs.CRS_JSON, fs_transform: FSTransformFn, try_build: bool) -> Iterable[Port]:
    tags = await github.get_repo_tags(owner, repo)
    print(f'Importing tags for {owner}/{repo}')
    tagged_versions = ((tag, util.tag_as_version(tag)) for tag in tags)
    return (  #
        SimpleGitHubAdaptingPort(
            package_id=PackageID(crs_json['name'], version, meta_version=1),
            owner=owner,
            repo=repo,
            tag=tag,
            crs_json=crs_json,
            fs_transform=fs_transform,
            try_build=try_build,
        )  #
        for tag, version in tagged_versions  #
        if version is not None and version >= min_version and version < max_version  #
    )


async def _null_transform(_p: Path) -> None:
    pass


async def enumerate_simple_github(
    *,
    owner: str,
    repo: str,
    namespace: str,
    min_version: VersionInfo = VersionInfo(0),
    max_version: VersionInfo = VersionInfo(99999999),
    package_name: Optional[str] = None,
    library_name: Optional[str] = None,
    depends: Optional[Sequence[str]] = None,
    uses: Optional[Sequence[str]] = None,
    fs_transform: Optional[FSTransformFn] = None,
    meta_version: int = 1,
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
            'meta_version':
            meta_version,
            'version':
            '[placeholder]',
            'namespace':
            namespace,
            'crs_version':
            1,
            'libraries': [{
                'path': '.',
                'name': library_name or repo,
                'uses': [],
                'depends': [crs.convert_dep_str(d, uses=(uses or [])) for d in (depends or [])],
            }],
        },
        fs_transform=fs_transform or _null_transform,
        try_build=try_build,
    )
