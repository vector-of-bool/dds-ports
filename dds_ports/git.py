"""
Git utilities
"""

from asyncio import Semaphore
from typing import AsyncIterator
from pathlib import Path
from contextlib import asynccontextmanager

from .port import PackageID
from .util import temporary_directory, run_process

CLONE_SEMAPHORE = Semaphore(4)


@asynccontextmanager
async def temporary_git_clone(url: str, tag_or_branch: str) -> AsyncIterator[Path]:
    with temporary_directory() as tdir:
        async with CLONE_SEMAPHORE:
            print(f'Cloning repository {url} at {tag_or_branch} into {tdir}')
            await run_process(['git', 'clone', '--quiet', f'--branch={tag_or_branch}', '--depth=1', url, str(tdir)])
        yield tdir


class SimpleGitPort:
    def __init__(self, pkg_id: PackageID, url: str, tag: str) -> None:
        self._pid = pkg_id
        self._url = url
        self._tag = tag

    @property
    def package_id(self) -> PackageID:
        """The ID of this simple git package"""
        return self._pid

    @asynccontextmanager
    async def prepare_sdist(self) -> AsyncIterator[Path]:
        async with temporary_git_clone(self._url, self._tag) as clone:
            yield clone

    def __repr__(self) -> str:
        return f'<SimpleGitPort package={self.package_id} url=[{self._url}]>'
