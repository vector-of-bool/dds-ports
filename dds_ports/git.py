"""
Git utilities
"""

from asyncio import Semaphore
from typing import AsyncIterator
from pathlib import Path
from contextlib import asynccontextmanager

import dagon.fs
import dagon.ui
import dagon.proc
import dagon.pool
from dagon import task

from .port import PackageID
from .util import temporary_directory, run_process

CLONE_SEMAPHORE = Semaphore(4)


@asynccontextmanager
async def temporary_git_clone(url: str, tag_or_branch: str) -> AsyncIterator[Path]:
    with temporary_directory(tag_or_branch) as tdir:
        async with CLONE_SEMAPHORE:
            print(f'Cloning repository {url} at {tag_or_branch} into {tdir}')
            await run_process(['git', 'clone', '--quiet', f'--branch={tag_or_branch}', '--depth=1', url, str(tdir)])
        yield tdir


class SimpleGitPort:
    def __init__(self, clone_key: str, pkg_id: PackageID, url: str, tag: str) -> None:
        self._clone_key = clone_key
        self._pid = pkg_id
        self._url = url
        self._tag = tag

    @property
    def package_id(self) -> PackageID:
        """The ID of this simple git package"""
        return self._pid

    async def _make_sdist(self, cloner: task.Task[Path]) -> Path:
        full_clone = await task.result_of(cloner)
        sub_clone: Path = full_clone.with_name(full_clone.name + f'@{self._tag}')
        await dagon.fs.remove(sub_clone, recurse=True, absent_ok=True)
        dagon.ui.status(f'Generating sdist for {self.package_id}')
        await dagon.proc.run(['git', 'clone', f'--branch={self._tag}', '--depth=1', full_clone.as_uri(), sub_clone])
        return sub_clone

    def make_prep_task(self) -> task.Task[Path]:
        cloner = get_git_cloner_task(self._clone_key, self._url)
        clone = task.fn_task(f'{self.package_id}@clone', lambda: self._make_sdist(cloner), depends=[cloner])
        dagon.pool.assign(clone, 'cloner')
        return clone

    def __repr__(self) -> str:
        return f'<SimpleGitPort package={self.package_id} url=[{self._url}]>'


async def _cached_clone(key: str, url: str) -> Path:
    clones_dir = Path('~/.cache/dds-ports/clones').expanduser()
    clones_dir.mkdir(exist_ok=True, parents=True)
    dest = clones_dir / key
    if dest.is_dir():
        dagon.ui.status(f'Re-fetching git repository {url}')
        await dagon.proc.run(['git', 'fetch', '--all'], cwd=dest)
        return dest
    tmp = dest.with_suffix('.tmp')
    dagon.ui.status(f'Cloning Git repository {url}')
    await dagon.proc.run(['git', 'clone', '--quiet', url, tmp])
    tmp.rename(dest)
    return dest


def get_git_cloner_task(key: str, url: str) -> task.Task[Path]:
    name = f'{key}@clone-all'
    try:
        t = task.fn_task(name, lambda: _cached_clone(key, url))
    except RuntimeError:
        return next(iter(t for t in task.dag.current_dag().tasks if t.name == name))
    dagon.pool.assign(t, 'cloner')
    return t
