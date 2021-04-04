import itertools
from typing import Iterable
import fnmatch
from pathlib import Path
import importlib.util

from .port import Port
from .util import wait_all


def find_port_files(dirpath: Path) -> Iterable[Path]:
    children = dirpath.iterdir()
    patterns = ('*_ports.py', '*_port.py')
    matching = (c.absolute().resolve() for c in children if any(fnmatch.fnmatchcase(c.name, p) for p in patterns))
    return matching


async def all_ports(dirpath: Path) -> Iterable[Port]:
    loading = (ports_in_file(fpath) for fpath in find_port_files(dirpath))
    ports = await wait_all(loading)
    return itertools.chain.from_iterable(ports)


async def ports_in_file(fpath: Path) -> Iterable[Port]:
    spec = importlib.util.spec_from_file_location(f'<portfile at {fpath}>', fpath)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)  # type: ignore
    return await module.all_ports()  # type: ignore
