import itertools
import re
import textwrap
from pathlib import Path
from typing import Iterable

from semver import VersionInfo

from dds_ports import auto, fs, github, port, util


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


async def fixup_taskflow(root: Path) -> None:
    await fs.move_files(files=root.glob('taskflow/**/*'), into=root / 'src/', whence=root)


async def fixup_immer(root: Path) -> None:
    await fs.move_files(files=root.glob('immer/**/*.hpp'), into=root / 'src', whence=root)
    config_hpp = root.joinpath('src/immer/config.hpp')
    config_lines = config_hpp.read_text().splitlines()
    ponce_pos = config_lines.index('#pragma once')
    config_lines.pop(ponce_pos)
    config_lines.insert(
        ponce_pos,
        textwrap.dedent(r'''
        #pragma once

        // This tweaks-include directive is not part of immer upstream, and was
        // added for the bpt port.
        #ifdef __has_include
            #if __has_include(<immer.tweaks.hpp>)
                #include <immer.tweaks.hpp>
            #endif
        #endif
        '''),
    )
    config_hpp.write_text('\n'.join(config_lines))


def _nvstdexec_tagmap(tag: str) -> VersionInfo | None:
    mat = re.match(r'nvhpc-(\d+)\.(\d+)(?:[-.](rc\d+))?', tag)
    if not mat:
        return
    maj, min, rc = mat.groups()
    return VersionInfo(int(maj), int(min), 0, rc)


async def all_ports() -> Iterable[port.Port]:
    return itertools.chain.from_iterable(await util.wait_all((
        auto.enumerate_simple_github(
            owner='zajo',
            repo='leaf',
            package_name='boost.leaf',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='boostorg',
            repo='mp11',
            package_name='boost.mp11',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='boostorg',
            repo='pfr',
            package_name='boost.pfr',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='hanickadot',
            repo='compile-time-regular-expressions',
            min_version=VersionInfo(2, 8, 1),
            package_name='ctre',
        ),
        auto.enumerate_simple_github(
            owner='fmtlib',
            repo='fmt',
            min_version=VersionInfo(6),
            max_version=VersionInfo(8),
        ),
        auto.enumerate_simple_github(
            owner='fmtlib',
            repo='fmt',
            min_version=VersionInfo(8),
            fs_transform=fixup_fmt_8,
        ),
        auto.enumerate_simple_github(
            owner='Neargye',
            repo='magic_enum',
            package_name='magic_enum',
        ),
        auto.enumerate_simple_github(
            owner='Neargye',
            repo='nameof',
            package_name='nameof',
        ),
        auto.enumerate_simple_github(
            owner='marzer',
            repo='tomlplusplus',
            package_name='tomlpp',
        ),
        auto.enumerate_simple_github(
            owner='ericniebler',
            repo='range-v3',
            package_name='range-v3',
        ),
        auto.enumerate_simple_github(
            owner='nlohmann',
            repo='json',
            min_version=VersionInfo(3, 5, 0),
            package_name='nlohmann-json',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='vector-of-bool',
            repo='wil',
            package_name='ms-wil',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='taocpp',
            repo='PEGTL',
            package_name='pegtl',
            min_version=VersionInfo(2, 6, 0),
            fs_transform=_remove_src,
        ),
        auto.enumerate_simple_github(
            owner='pantor',
            repo='inja',
            package_name='inja',
            depends=['nlohmann-json^3.0.0 using nlohmann-json'],
            min_version=VersionInfo(2, 1, 0),
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='USCiLab',
            repo='cereal',
            package_name='cereal',
            min_version=VersionInfo(0, 9, 0),
        ),
        auto.enumerate_simple_github(
            owner='pybind',
            repo='pybind11',
            package_name='pybind11',
            min_version=VersionInfo(2, 0, 0),
        ),
        auto.enumerate_simple_github(
            owner='imneme',
            repo='pcg-cpp',
            package_name='pcg-cpp',
            min_version=VersionInfo(0, 98, 1),
        ),
        auto.enumerate_simple_github(
            owner='HowardHinnant',
            repo='date',
            package_name='hinnant-date',
            min_version=VersionInfo(2, 4, 1),
            fs_transform=_remove_src,
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='lua',
            repo='lua',
            min_version=VersionInfo(5, 1, 1),
            fs_transform=move_sources_into_src,
        ),
        auto.enumerate_simple_github(
            owner='ThePhD',
            repo='sol2',
            min_version=VersionInfo(3),
            depends=['lua^5.0.0 using lua'],
        ),
        auto.enumerate_simple_github(
            owner='gabime',
            repo='spdlog',
            depends=['fmt+6.0.0 using fmt'],
            min_version=VersionInfo(1, 4, 0),
            fs_transform=fixup_spdlog,
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='soasis',
            repo='text',
            package_name='ztd.text',
            pkg_version=2,
        ),
        auto.enumerate_simple_github(
            owner='taskflow',
            repo='taskflow',
            fs_transform=fixup_taskflow,
        ),
        auto.enumerate_simple_github(
            owner='jbeder',
            repo='yaml-cpp',
            min_version=VersionInfo(0, 6, 0),
        ),
        auto.enumerate_simple_github(
            owner='arximboldi',
            repo='immer',
            fs_transform=fixup_immer,
        ),
        auto.enumerate_simple_github(
            owner='NVIDIA',
            repo='stdexec',
            tag_mapper=_nvstdexec_tagmap,
        ),
        github.native_bpt_ports_for_github_repo(
            owner='vector-of-bool',
            repo='debate',
            pkg_name='vob.debate',
        ),
    )))
