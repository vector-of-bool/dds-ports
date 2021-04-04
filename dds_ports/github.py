from asyncio import Semaphore
import os
from typing import Any, AsyncContextManager, Iterable, Optional

from aiohttp import client
from semver import VersionInfo

from .port import Port, PackageID
from .git import SimpleGitPort
from .util import tag_as_version, drop_nones

HTTP_SESSION = client.ClientSession()
HTTP_SEMAPHORE = Semaphore(6)


async def github_http_get(path: str) -> Any:
    token = os.getenv('GITHUB_API_TOKEN')
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


async def repo_tags_as_versions(owner: str, repo: str) -> Iterable[VersionInfo]:
    tags = await get_repo_tags(owner, repo)
    return drop_nones(tag_as_version(t) for t in tags)


def _tags_as_ports(tags: Iterable[str], owner: str, repo: str, pkg_name: Optional[str],
                   min_version: VersionInfo) -> Iterable[Port]:
    for t in tags:
        ver = tag_as_version(t)
        if ver is None or ver < min_version:
            continue
        pid = PackageID(name=pkg_name or repo, version=ver)
        yield SimpleGitPort(pid, f'https://github.com/{owner}/{repo}.git', t)


async def native_dds_ports_for_github_repo(*,
                                           owner: str,
                                           repo: str,
                                           pkg_name: Optional[str] = None,
                                           min_version: VersionInfo = VersionInfo(0)) -> Iterable[Port]:
    tags = await get_repo_tags(owner, repo)
    print(f'Generating ports for {owner}/{repo}')
    return _tags_as_ports(tags, owner, repo, pkg_name, min_version)
