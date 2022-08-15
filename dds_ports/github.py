from asyncio import Semaphore
import os
from typing import Any, AsyncContextManager, Callable, Iterable, Optional, TypeVar

from aiohttp import client
from semver import VersionInfo

from dds_ports.git import SimpleGitPort
from dds_ports.legacy import LegacyDDSGitPort

from .port import Port, PackageID
from .util import tag_as_version

HTTP_SESSION = client.ClientSession()
HTTP_SEMAPHORE = Semaphore(6)


async def github_http_get(path: str) -> Any:
    token = os.getenv('GITHUB_API_TOKEN', os.getenv('GITHUB_TOKEN'))
    if token is None:
        raise RuntimeError('Set a GITHUB_API_TOKEN environment variable to talk with GitHub, please')
    headers = {
        'Accept-Encoding': 'application/json',
        'Authorization': f'token {token}',
    }
    url = f'https://api.github.com{path}'
    async with HTTP_SEMAPHORE:
        resp = await HTTP_SESSION.get(url, headers=headers)
        return await resp.json()


async def get_repo_tags(owner: str, repo: str) -> Iterable[str]:
    print(f'Collecting tags for GitHub repo {owner}/{repo}')
    resp = await github_http_get(f'/repos/{owner}/{repo}/tags')
    return (t['name'] for t in resp)


def session_context_manager() -> AsyncContextManager[client.ClientSession]:
    return HTTP_SESSION


def _each_tag_as_version(owner: str, repo: str, tags: Iterable[str]) -> Iterable[VersionInfo]:
    for t in tags:
        ver = tag_as_version(t)
        if ver is None:
            print(f'Skipping tag "{t}" in {owner}/{repo}')
            continue
        yield ver


async def repo_tags_as_versions(owner: str, repo: str) -> Iterable[VersionInfo]:
    tags = await get_repo_tags(owner, repo)
    return _each_tag_as_version(owner, repo, tags)


PortTypeT = TypeVar('PortTypeT', bound=SimpleGitPort)
_PortFactory = Callable[[str, PackageID, str, str], PortTypeT]


def _tags_as_ports(tags: Iterable[str],
                   owner: str,
                   repo: str,
                   pkg_name: Optional[str],
                   min_version: VersionInfo,
                   max_version: VersionInfo | None,
                   revision: int = 1,
                   *,
                   porttype: _PortFactory[PortTypeT]) -> Iterable[PortTypeT]:
    for t in tags:
        ver = tag_as_version(t)
        if ver is None:
            print(f'Skipping tag "{ver}" in {owner}/{repo}')
            continue
        if ver is None or ver < min_version:
            continue
        if max_version is not None and ver >= max_version:
            continue
        pid = PackageID(name=pkg_name or repo, version=ver, revision=revision)
        yield porttype(pid.name, pid, gh_repo_url(owner, repo), t)


def gh_repo_url(owner: str, repo: str) -> str:
    return f'https://github.com/{owner}/{repo}.git'


async def native_dds_ports_for_github_repo(*,
                                           owner: str,
                                           repo: str,
                                           pkg_name: Optional[str] = None,
                                           min_version: VersionInfo = VersionInfo(0),
                                           max_version: VersionInfo | None = None,
                                           revision: int = 1) -> Iterable[Port]:
    tags = await get_repo_tags(owner, repo)
    print(f'Generating ports for {owner}/{repo}')
    return _tags_as_ports(tags, owner, repo, pkg_name, min_version, max_version, revision, porttype=LegacyDDSGitPort)


async def native_bpt_ports_for_github_repo(*,
                                           owner: str,
                                           repo: str,
                                           pkg_name: str | None = None,
                                           min_version: VersionInfo = VersionInfo(0),
                                           max_version: VersionInfo | None = None,
                                           revision: int = 1) -> Iterable[Port]:
    tags = await get_repo_tags(owner, repo)
    return _tags_as_ports(tags, owner, repo, pkg_name, min_version, max_version, revision, porttype=SimpleGitPort)
