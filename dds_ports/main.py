from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable, NoReturn, Sequence, cast

import dagon.proc
import dagon.ext.exec
import dagon.ext.loader
import dagon.pool
import dagon.tool.main
import dagon.ui
from dagon import proc, task
from dagon.task import TaskDAG
from dagon.task.dag import populate_dag_context
from typing_extensions import Protocol

from .collect import collect_ports
from .github import session_context_manager
from .port import Port, PackageID
from .repo import RepositoryAccess


class CommandArguments(Protocol):
    ports_dir: Path
    repo_dir: Path


async def _init_all_ports(dirpath: Path) -> Iterable[Port]:
    async with session_context_manager():
        return await collect_ports(dirpath)


async def _import_from(repo: RepositoryAccess, pkgs: Iterable[task.Task[Path]]) -> None:
    dirs = [await task.result_of(t) for t in pkgs]
    dagon.ui.status('Importing packages...')
    await proc.run(['./dds', 'repo', 'import', str(repo.directory), *dirs, '--if-exists=replace'], on_output='status')


def make_importer(repo: RepositoryAccess, id: PackageID, prepper: task.Task[Path]) -> task.Task[None]:
    return task.fn_task(f'{id}:import', lambda: _import_from(repo, [prepper]), depends=[prepper])


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ports-dir', type=Path, required=True, help='Root directory of the ports directories')
    parser.add_argument('--repo-dir', type=Path, required=True, help='Directory containing the dds repository')
    args = cast(CommandArguments, parser.parse_args(argv))
    dag = TaskDAG('<dds-ports-mkrepo>')
    ports = asyncio.get_event_loop().run_until_complete(_init_all_ports(args.ports_dir))
    import_pkgs: list[task.Task[None]] = []

    repo = RepositoryAccess.open(args.repo_dir)
    exts = dagon.tool.main.get_extensions()
    with exts.app_context():
        dagon.pool.add('cloner', 3)
        dagon.pool.add('importer', 10)
        with populate_dag_context(dag):
            for p in ports:
                prepper = p.make_prep_task()
                if p.package_id in repo.packages:
                    continue
                importer = make_importer(repo, p.package_id, prepper)
                dagon.pool.assign(importer, 'importer')
                import_pkgs.append(importer)

            validate = dagon.proc.cmd_task('validate-repo', ['./dds', 'repo', 'validate', repo.directory],
                                           on_output='status',
                                           depends=import_pkgs)
            task.gather('all', [validate])

        i: int = dagon.tool.main.run_for_dag(dag, exts, argv=[], default_tasks=['all'])
        return i


def start() -> NoReturn:
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    start()
