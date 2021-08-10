import argparse
import asyncio
from pathlib import Path
from typing import Sequence, NoReturn
from typing_extensions import Protocol
import sys

import json5
from semver import VersionInfo

from .port import Port, PackageID
from .collect import all_ports
from .github import session_context_manager
from .util import wait_all, temporary_directory, run_process
from .repo import RepositoryAccess


class CommandArguments(Protocol):
    ports_dir: Path
    repo_dir: Path


def check_sdist(pid: PackageID, dirpath: Path) -> None:
    cand_files = ('package.json', 'package.json5', 'package.jsonc')
    candidates = (dirpath / fname for fname in cand_files)
    found = [c for c in candidates if c.is_file()]
    if not found:
        raise RuntimeError(f'Port for {pid} did not produce a package JSON manifest file')

    content = json5.loads(found[0].read_text())
    if not isinstance(content, dict) or not 'name' in content or not 'version' in content:
        raise RuntimeError(f'Package manifest for {pid} is invalid (Got: {content})')
    try:
        manver = VersionInfo.parse(content['version'])
    except ValueError as e:
        raise RuntimeError(f'"version" for {pid} is not a valid semantic version (Got {content["version"]})') from e
    if content['name'] != pid.name:
        raise RuntimeError(f'Package manifest for {pid} declares different name "{content["name"]}')
    if manver != pid.version:
        raise RuntimeError(f'Package manifest for {pid} declares a different version [{manver}]')

    if all(not dirpath.joinpath(sub).is_dir() for sub in ('include', 'src', 'libs')):
        raise RuntimeError(f'Package {pid} does not contain either a src/, include/, or libs/ directory')
    print(f'Package {pid} is OK')


async def _import_port(port: Port, repo: RepositoryAccess) -> None:
    if port.package_id in repo.packages:
        print('Skipping import of already-imported package:', port.package_id)
        return
    async with port.prepare_sdist() as sdist_dir:
        check_sdist(port.package_id, sdist_dir)
        with temporary_directory() as sd_create_dir:
            sd_file = sd_create_dir / f'{port.package_id}.tar.gz'
            print(f'Archiving {port.package_id}...')
            await run_process(['./dds', 'pkg', 'create', f'--project={sdist_dir}', f'--out={sd_file}'])
            print(f'Storing {port.package_id}')
            await run_process(['./dds', 'repoman', 'import', str(repo.directory), str(sd_file)])


async def _main(args: CommandArguments) -> int:
    repo = await RepositoryAccess.open(args.repo_dir)

    async with session_context_manager():
        found = await all_ports(args.ports_dir)
        await wait_all(_import_port(p, repo) for p in found)

    return 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ports-dir', type=Path, required=True, help='Root directory of the ports directories')
    parser.add_argument('--repo-dir', type=Path, required=True, help='Directory containing the dds repository')
    args: CommandArguments = parser.parse_args(argv)
    return asyncio.get_event_loop().run_until_complete(_main(args))


def start() -> NoReturn:
    sys.exit(main(sys.argv[1:]))
