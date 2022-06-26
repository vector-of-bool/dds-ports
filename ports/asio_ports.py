from pathlib import Path
from semver import VersionInfo
import re

from dds_ports import auto, port, fs, github, crs


async def fixup_asio(root: Path) -> None:
    root.joinpath('asio/include').rename(root / 'include')
    root.joinpath('asio/src').rename(root / 'src')
    rm_dirs = (
        'doc',
        'examples',
        'tests',
        'tools',
    )
    for d in rm_dirs:
        await fs.remove_directory(root / 'src' / d)

    config_hpp = root / 'include/asio/detail/config.hpp'
    config_hpp_lines = config_hpp.read_text().splitlines()
    config_hpp_lines.insert(13, '#define ASIO_STANDALONE 1')
    config_hpp_lines.insert(14, '#define ASIO_SEPARATE_COMPILATION 1')
    config_hpp.write_text('\n'.join(config_hpp_lines))


async def all_ports() -> port.PortIter:
    owner = 'chriskohlhoff'
    tags = await github.get_repo_tags(owner, 'asio')
    tag_re = re.compile(r'asio-(\d+)-(\d+)-(\d+)')
    version_strs = ((tag, tag_re.sub(r'\1.\2.\3', tag)) for tag in tags)
    versions = ((tag, VersionInfo.parse(ver_str)) for tag, ver_str in version_strs)

    return (auto.SimpleGitHubAdaptingPort(
        package_id=port.PackageID('asio', version, 1),
        owner=owner,
        repo='asio',
        tag=tag,
        crs_json=crs.simple_placeholder_json('asio'),
        fs_transform=fixup_asio,
        try_build=version != VersionInfo(1, 16, 0),
    ) for tag, version in versions if version >= VersionInfo(1, 12, 0))
