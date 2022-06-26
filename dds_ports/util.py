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

TAG_VERSION_RE = re.compile(r'(?:v|boost-|yaml-cpp-|release-|pegtl-)?(\d+\.\d+(\.\d+)?([-.].*|$))')


async def wait_all(futs: Iterable[Awaitable[T]]) -> Iterable[T]:
    return await asyncio.gather(*futs)


def tag_as_version(tag: str) -> Optional[VersionInfo]:
    mat = TAG_VERSION_RE.match(tag)
    if not mat:
        return None
    ver_str = mat.group(1)
    ver_str = re.sub(r'^(\d+\.\d+)($|-)', r'\1.0\2', ver_str)
    ver_str = re.sub(r'^(\d+\.\d+\.\d+)\.', r'\1-', ver_str)
    try:
        return VersionInfo.parse(ver_str)
    except ValueError:
        print(f'Failed to parse version-like tag "{tag}" ({ver_str})')
        return None


@contextmanager
def temporary_directory(suffix: str = 'dds-ports') -> Iterator[Path]:
    """
    Obtain a temporary directory that will be automatically deleted
    """
    tdir = Path(tempfile.mkdtemp(suffix='-' + suffix))
    try:
        tdir.mkdir(exist_ok=True, parents=True)
        yield tdir
    finally:
        shutil.rmtree(tdir)


async def run_process(command: Sequence[str]) -> None:
    proc = await asyncio.create_subprocess_exec(*command,
                                                stdin=asyncio.subprocess.PIPE,
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT)
    output, _ = await proc.communicate()
    retc = await proc.wait()
    if retc != 0:
        print(f'Subprocess {command} failed:\n{output.decode()}')
        raise subprocess.CalledProcessError(retc, command, output=output)
