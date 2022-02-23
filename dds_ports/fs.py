import asyncio
import concurrent.futures
from typing import Awaitable, TypeVar, Callable, Iterable
from pathlib import Path
import shutil

_FS_POOL = concurrent.futures.ThreadPoolExecutor(8)

T = TypeVar('T')


def _run_fs_op(op: Callable[[], T]) -> Awaitable[T]:
    return asyncio.get_running_loop().run_in_executor(_FS_POOL, op)


async def remove_directory(dirpath: Path) -> None:
    await _run_fs_op(lambda: shutil.rmtree(dirpath))


def _remove_files(files: Iterable[Path]) -> None:
    for f in files:
        f.unlink()


async def remove_files(files: Iterable[Path]) -> None:
    await _run_fs_op(lambda: _remove_files(files))


def _move_files(*, into: Path, files: Iterable[Path], whence: Path) -> None:
    files = list(files)
    for src_path in files:
        relpath = src_path.relative_to(whence)
        if relpath.parts[0] == '..':
            raise RuntimeError(f'Cannot move file [{src_path}] relative to non-parent directory at [{whence}]')

        dest_path = into / relpath

        if src_path.is_dir():
            dest_path.mkdir(exist_ok=True, parents=True)
        else:
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            src_path.rename(dest_path)


async def move_files(*, into: Path, files: Iterable[Path], whence: Path) -> None:
    await _run_fs_op(lambda: _move_files(into=into, files=files, whence=whence))


def _copy_files(*, into: Path, files: Iterable[Path], whence: Path) -> None:
    files = list(files)
    for src_path in files:
        relpath = src_path.relative_to(whence)
        if relpath.parts[0] == '..':
            raise RuntimeError(f'Cannot copy file [{src_path}] relative to non-parent directory at [{whence}]')

        dest_path = into / relpath

        if src_path.is_dir():
            dest_path.mkdir(exist_ok=True, parents=True)
        else:
            dest_path.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(src_path, dest_path)


async def copy_files(*, into: Path, files: Iterable[Path], whence: Path) -> None:
    await _run_fs_op(lambda: _copy_files(into=into, files=files, whence=whence))
