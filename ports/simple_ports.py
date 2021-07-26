from pathlib import Path
import itertools
from typing import Iterable
from semver import VersionInfo

from dds_ports import port, auto, util, fs


async def _remove_src(root: Path) -> None:
    "Removes the `src/` directory from a package root"
    await fs.remove_directory(root / 'src/')


async def move_sources_into_src(root: Path) -> None:
    "Move source files in the root directory into src/"
    await fs.move_files(
        files=itertools.chain(root.glob('*.c'), root.glob('*.h')),
        into=root / 'src/',
        whence=root,
    )


async def fixup_spdlog(root: Path) -> None:
    await _remove_src(root)
    tweakme_h = root / 'include/spdlog/tweakme.h'
    tweakme_h_lines = tweakme_h.read_text().splitlines()
    tweakme_h_lines.insert(13, '#define SPDLOG_FMT_EXTERNAL 1')
    tweakme_h.write_text('\n'.join(tweakme_h_lines))


async def fixup_fmt_8(root: Path) -> None:
    # Delete fmt.cc, which was added in fmt@8 and is a C++ module unit, which
    # dds cannot yet handle
    await fs.remove_files([Path(root / 'src/fmt.cc')])


async def all_ports() -> Iterable[port.Port]:
    return itertools.chain.from_iterable(await util.wait_all((
        auto.enumerate_simple_github(
            owner='zajo',
            repo='leaf',
            package_name='boost.leaf',
            library_name='leaf',
            namespace='boost',
        ),
        auto.enumerate_simple_github(
            owner='boostorg',
            repo='mp11',
            namespace='boost',
            package_name='boost.mp11',
            library_name='mp11',
        ),
        auto.enumerate_simple_github(
            owner='apolukhin',
            repo='magic_get',
            namespace='boost',
            package_name='boost.pfr',
            library_name='pft',
        ),
        auto.enumerate_simple_github(
            owner='hanickadot',
            repo='compile-time-regular-expressions',
            min_version=VersionInfo(2, 8, 1),
            package_name='ctre',
            namespace='hanickadot',
            library_name='ctre',
        ),
        auto.enumerate_simple_github(
            owner='fmtlib',
            repo='fmt',
            namespace='fmt',
            min_version=VersionInfo(6),
            fs_transform=fixup_fmt_8,
        ),
        auto.enumerate_simple_github(
            owner='Neargye',
            repo='magic_enum',
            package_name='magic_enum',
            namespace='neargye',
            library_name='magic_enum',
        ),
        auto.enumerate_simple_github(
            owner='Neargye',
            repo='nameof',
            package_name='nameof',
            namespace='neargye',
            library_name='nameof',
        ),
        auto.enumerate_simple_github(
            owner='marzer',
            repo='tomlplusplus',
            namespace='tomlpp',
            package_name='tomlpp',
            library_name='tomlpp',
        ),
        auto.enumerate_simple_github(
            owner='ericniebler',
            repo='range-v3',
            package_name='range-v3',
            namespace='range-v3',
            library_name='range-v3',
        ),
        auto.enumerate_simple_github(
            owner='nlohmann',
            repo='json',
            min_version=VersionInfo(3, 5, 0),
            package_name='nlohmann-json',
            namespace='nlohmann',
            library_name='json',
        ),
        auto.enumerate_simple_github(
            owner='vector-of-bool',
            repo='wil',
            package_name='ms-wil',
            namespace='microsoft',
            library_name='wil',
        ),
        auto.enumerate_simple_github(
            owner='taocpp',
            repo='PEGTL',
            package_name='pegtl',
            namespace='tao',
            library_name='pegtl',
            min_version=VersionInfo(2, 6, 0),
            fs_transform=_remove_src,
        ),
        auto.enumerate_simple_github(
            owner='pantor',
            repo='inja',
            package_name='inja',
            namespace='inja',
            library_name='inja',
            depends=['nlohmann-json@3.0.0'],
            min_version=VersionInfo(2, 1, 0),
            uses=['nlohmann/json'],
        ),
        auto.enumerate_simple_github(
            owner='USCiLab',
            repo='cereal',
            package_name='cereal',
            namespace='cereal',
            library_name='cereal',
            min_version=VersionInfo(0, 9, 0),
        ),
        auto.enumerate_simple_github(
            owner='pybind',
            repo='pybind11',
            package_name='pybind11',
            namespace='pybind',
            library_name='pybind11',
            min_version=VersionInfo(2, 0, 0),
        ),
        auto.enumerate_simple_github(
            owner='imneme',
            repo='pcg-cpp',
            package_name='pcg-cpp',
            namespace='pcg',
            library_name='pcg-cpp',
            min_version=VersionInfo(0, 98, 1),
        ),
        auto.enumerate_simple_github(
            owner='HowardHinnant',
            repo='date',
            package_name='hinnant-date',
            namespace='hinnant',
            library_name='date',
            min_version=VersionInfo(2, 4, 1),
            fs_transform=_remove_src,
        ),
        auto.enumerate_simple_github(
            owner='lua',
            repo='lua',
            namespace='lua',
            min_version=VersionInfo(5, 1, 1),
            fs_transform=move_sources_into_src,
        ),
        auto.enumerate_simple_github(
            owner='ThePhD',
            repo='sol2',
            namespace='sol2',
            min_version=VersionInfo(3),
            depends=['lua@5.0.0'],
            uses=['lua/lua'],
        ),
        auto.enumerate_simple_github(
            owner='gabime',
            repo='spdlog',
            namespace='spdlog',
            depends=['fmt@6.0.0'],
            uses=['fmt/fmt'],
            min_version=VersionInfo(1, 4, 0),
            fs_transform=fixup_spdlog,
        ),
        auto.enumerate_simple_github(
            owner='soasis',
            repo='text',
            package_name='ztd.text',
            namespace='ztd',
            library_name='text',
        ),
    )))
