from __future__ import annotations

from typing_extensions import Literal, TypedDict
from pathlib import Path
import json
import re

import semver

CRS_DepVersionRange = TypedDict('CRS_DepVersionRange', {
    'low': str,
    'high': str,
})
CRS_Dependency = TypedDict('CRS_Dependency', {
    'name': str,
    'versions': 'list[CRS_DepVersionRange]',
    'using': 'list[str]',
})
CRS_Library = TypedDict(
    'CRS_Library', {
        'path': str,
        'name': str,
        'dependencies': 'list[CRS_Dependency]',
        'test-dependencies': 'list[CRS_Dependency]',
        'using': 'list[str]',
        'test-using': 'list[str]',
    })

CRS_JSON = TypedDict('CRS_JSON', {
    'name': str,
    'version': str,
    'pkg-version': int,
    'libraries': 'list[CRS_Library]',
    'schema-version': Literal[1],
})

_DEP_SPLIT_RE = re.compile(r'^(.+?)([@^~+])(.+) using ((?:[\w\.-]+)(?:, [\w\.-]+)*)$')


def convert_dep_str(dep: str) -> CRS_Dependency:
    mat = _DEP_SPLIT_RE.match(dep)
    assert mat, (dep, 'Invalid dependency shorthand string. Should be "<name>[@^~+]<version> using [<lib>[, ...]]')
    name, tag, version_str, using_ = mat.groups()
    using = using_.split(', ')
    version = semver.VersionInfo.parse(version_str)
    hi_version = semver.VersionInfo(0)
    if tag == '@':
        hi_version = version.bump_patch()
    elif tag == '~':
        hi_version = version.bump_major()
    elif tag == '^':
        hi_version = version.bump_major()
    elif tag == '+':
        hi_version = semver.VersionInfo(999999)
    else:
        assert 0, (dep, tag)
    return {
        'name': str(name),
        'versions': [{
            'low': str(version),
            'high': str(hi_version),
        }],
        'using': list(using),
    }


def write_crs_file(dirpath: Path, content: CRS_JSON) -> Path:
    dest = dirpath / 'pkg.json'
    dest.write_text(json.dumps(content, indent=2))
    return dest


def simple_placeholder_json(library: str) -> CRS_JSON:
    return {
        'name':
        '[placeholder]',
        'version':
        '[placeholder]',
        'pkg-version':
        -1,
        'libraries': [{
            'name': library,
            'path': '.',
            'using': [],
            'test-using': [],
            'dependencies': [],
            'test-dependencies': [],
        }],
        'schema-version':
        1,
    }
