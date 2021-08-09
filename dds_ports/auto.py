from asyncio import Semaphore
from contextlib import asynccontextmanager
from pathlib import Path
import json
from typing import Callable, Iterable, Sequence, Optional, NamedTuple, AsyncIterator, Any, Awaitable
from typing_extensions import TypedDict

from semver import VersionInfo

from dds_ports.port import Port, PackageID
from dds_ports import git, github, util

PackageJSON = TypedDict('PackageJSON', {
    'name': str,
    'namespace': str,
    'depends': Sequence[str],
})

LibraryJSON = TypedDict('LibraryJSON', {
    'name': str,
    'uses': Sequence[str],
})

FSTransformFn = Callable[[Path], Awaitable[None]]

BUILD_SEMAPHORE = Semaphore(1)


class SimpleGitAdaptingPort:
    def __init__(self,
                 package_id: PackageID,
                 url: str,
                 tag: str,
                 package_json: PackageJSON,
                 library_json: LibraryJSON,
                 fs_transform: FSTransformFn,
                 try_build: bool):
        self.package_id = package_id
        self.url = url
        self.tag = tag
        self.package_json = package_json
        self.library_json = library_json
        self.fs_transform = fs_transform
        self.try_build = try_build

    @asynccontextmanager
    async def prepare_sdist(self) -> AsyncIterator[Path]:
        git_port = git.SimpleGitPort(self.package_id, self.url, self.tag)
        async with git_port.prepare_sdist() as clone:
            full_pkg_json: Any = self.package_json
            full_pkg_json['version'] = str(self.package_id.version)
            clone.joinpath('package.json').write_text(
                json.dumps(full_pkg_json, indent=2))
            clone.joinpath('library.json').write_text(
                json.dumps(self.library_json, indent=2))
            await self.fs_transform(clone)
            if self.try_build:
                async with BUILD_SEMAPHORE:
                    print(f'Attempting a build of {self.package_id}...')
                    await util.run_process(
                        ['./dds', 'build', '--no-tests', f'--project={clone}', f'--out={clone/"_build"}'])
            yield clone


class SimpleGitHubAdaptingPort(SimpleGitAdaptingPort):
    def __init__(self, *, owner: str, repo: str, **kwargs):
        self.owner = owner
        self.repo = repo
        super().__init__(
            **kwargs, url=f'https://github.com/{self.owner}/{self.repo}.git')


async def get_repo_ports(owner: str, repo: str, *, min_version: VersionInfo, package_json: PackageJSON,
                         lib_json: LibraryJSON, fs_transform: FSTransformFn, try_build: bool) -> Iterable[Port]:
    tags = await github.get_repo_tags(owner, repo)
    print(f'Importing tags for {owner}/{repo}')
    tagged_versions = ((tag, util.tag_as_version(tag)) for tag in tags)
    return (  #
        SimpleGitHubAdaptingPort(
            package_id=PackageID(package_json['name'], version),
            owner=owner,
            repo=repo,
            tag=tag,
            package_json=package_json,
            library_json=lib_json,
            fs_transform=fs_transform,
            try_build=try_build,
        )  #
        for tag, version in tagged_versions  #
        if version is not None and version >= min_version  #
    )


async def _null_transform(_p: Path) -> None:
    pass


async def enumerate_simple_github(
    *,
    owner: str,
    repo: str,
    namespace: str,
    min_version: VersionInfo = VersionInfo(0),
    package_name: Optional[str] = None,
    library_name: Optional[str] = None,
    depends: Optional[Sequence[str]] = None,
    uses: Optional[Sequence[str]] = None,
    fs_transform: Optional[FSTransformFn] = None,
    try_build: bool = True,
) -> Iterable[Port]:
    return await get_repo_ports(
        owner,
        repo,
        min_version=min_version,
        package_json={
            'name': package_name or repo,
            'namespace': namespace,
            'depends': list(depends or []),
        },
        lib_json={
            'name': library_name or repo,
            'uses': list(uses or []),
        },
        fs_transform=fs_transform or _null_transform,
        try_build=try_build,
    )
