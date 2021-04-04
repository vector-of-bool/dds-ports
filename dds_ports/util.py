import asyncio
from pathlib import Path
from typing import TypeVar, Iterable, Awaitable, Iterator, Sequence, Optional
import tempfile
import shutil
from contextlib import contextmanager
import subprocess
import re

from semver import VersionInfo

T = TypeVar('T')

TAG_VERSION_RE = re.compile(r'v?(\d+\.\d+(\.\d+)?(-.*|$))')


async def wait_all(futs: Iterable[Awaitable[T]]) -> Iterable[T]:
    return await asyncio.gather(*futs)


def tag_as_version(tag: str) -> Optional[VersionInfo]:
    mat = TAG_VERSION_RE.match(tag)
    if not mat:
        print(f'Skipping non-version tag: {tag}')
        return None
    ver_str = mat.group(1)
    try:
        return VersionInfo.parse(ver_str)
    except ValueError:
        print(f'Failed to parse version-like tag "{tag}"')
        return None


def drop_nones(it: Iterable[Optional[T]]) -> Iterable[T]:
    return (item for item in it if item is not None)


@contextmanager
def temporary_directory() -> Iterator[Path]:
    """
    Obtain a temporary directory that will be automatically deleted
    """
    tdir = Path(tempfile.mkdtemp(suffix='-dds-ports'))
    try:
        tdir.mkdir(exist_ok=True, parents=True)
        yield tdir
    finally:
        shutil.rmtree(tdir)


async def run_process(command: Sequence[str]) -> None:
    proc = await asyncio.create_subprocess_exec(*command,
                                                stdin=asyncio.subprocess.PIPE,
                                                stdout=None,
                                                stderr=asyncio.subprocess.STDOUT)
    output, _ = await proc.communicate()
    retc = await proc.wait()
    if retc != 0:
        print(f'Subprocess {command} failed:\n{output.decode()}')
        raise subprocess.CalledProcessError(retc, command, output=output)
