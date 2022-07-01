from __future__ import annotations

import itertools
import re
import textwrap
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence, Union

from dds_ports import crs, fs, git, github, port
from semver import VersionInfo

IMGUI_PORT_REVISION = 1

CONFIG_INCLUDE_TWEAKS = r'''
#pragma once

/* This tweaks-header #include was inserted by the bpt port */
#if defined(__has_include)
  #if __has_include(<imgui.tweaks.h>)
    #include <imgui.tweaks.h>
  #endif
#endif
'''


class HasInclude(NamedTuple):
    header: str

    def render(self) -> str:
        return f'__has_include({self.header})'


class IsDefined(NamedTuple):
    macro: str

    def render(self) -> str:
        return f'defined({self.macro})'


class Both(NamedTuple):
    left: Condition
    right: Condition

    def render(self) -> str:
        return f'({self.left.render()} && {self.right.render()})'


class Either(NamedTuple):
    left: Condition
    right: Condition

    def render(self) -> str:
        return f'({self.left.render()} || {self.right.render()})'


Condition = Union[IsDefined, HasInclude, Both, Either]


class BackendInfo(NamedTuple):
    name: str
    patterns: Sequence[str]
    condition: Condition | None
    added_in: VersionInfo | None = None

    using: Sequence[str] = ()

    @property
    def lib_name(self):
        """The full library name"""
        return f'backend.{self.name}'


def has_includes_cond(*headers: str) -> Condition:
    if len(headers) > 1:
        return Both(HasInclude(headers[0]), has_includes_cond(*headers[1:]))
    else:
        return HasInclude(headers[0])


IS_EMBEDDED_APPLE = Both(IsDefined('__APPLE__'), Either(IsDefined('TARGET_OS_IOS'), IsDefined('TARGET_OS_TV')))

backends: Sequence[BackendInfo] = [
    BackendInfo(
        'allegro5',
        [
            'imgui_impl_allegro5.*',
            # Old name used in some versions:
            'imgui_impl_a5.*',
        ],
        has_includes_cond('<allegro5/allegro.h>', '<allegro5/allegro_primitives.h>'),
        added_in=VersionInfo(1, 61),
    ),
    BackendInfo('android', ['imgui_impl_android.*'],
                has_includes_cond(*(f'<android/{f}.h>' for f in ('native_window', 'keycodes', 'input', 'log')))),
    BackendInfo('dx9', ['imgui_impl_dx9.*'], has_includes_cond('<d3d9.h>')),
    BackendInfo('dx10', ['imgui_impl_dx10.*'], has_includes_cond('<d3d10_1.h>', '<d3d10.h>', '<d3dcompiler.h>')),
    BackendInfo('dx11', ['imgui_impl_dx11.*'], has_includes_cond('<d3d11.h>', '<d3dcompiler.h>')),
    BackendInfo('dx12', ['imgui_impl_dx12.*'], has_includes_cond('<d3d12.h>', '<dxgi1_4.h>', '<d3dcompiler.h>')),
    BackendInfo('glfw', ['imgui_impl_glfw.*'], HasInclude('<GLFW/glfw3.h>')),
    BackendInfo('metal', ['imgui_impl_metal.*'], HasInclude('<Metal/Metal.h>')),
    BackendInfo('opengl2', ['imgui_impl_opengl2.*'],
                Either(Both(IsDefined('__APPLE__'), HasInclude('<OpenGL/gl.h>')), HasInclude('<GL/gl.h>'))),
    BackendInfo(
        'opengl3',
        ['imgui_impl_opengl3.*', 'imgui_impl_opengl3_loader.*'],
        Either(
            Both(
                IsDefined('IMGUI_IMPL_OPENGL_ES2'),
                # We want OpenGL ES2
                Either(
                    Both(
                        IS_EMBEDDED_APPLE,
                        HasInclude('<OpenGLES/ES2/gl.h>'),
                    ),
                    # Other platforms:
                    HasInclude('<GLES2/gl2.h>'),
                ),
            ),
            Either(
                # Detect Emscripten
                Both(IsDefined('__EMSCRIPTEN__'), HasInclude('<GLES2/gl2ext.h>')),
                # Not Emscripten:
                Either(
                    # Embedded apple:
                    Both(IS_EMBEDDED_APPLE, HasInclude('<OpenGLES/ES3/gl.h>')),
                    # Other:
                    HasInclude('<GLES3/gl3.h>')),
            ),
        ),
    ),
    # BackendInfo('osx', ['imgui_impl_osx.*'],
    #             has_includes_cond('<Cocoa/Cocoa.h>', '<Carbon/Carbon.h>', '<GameController/GameController.h>')),
    BackendInfo('sdl', ['imgui_impl_sdl.*'], has_includes_cond('<SDL.h>', '<SDL_syswm.h>')),
    BackendInfo('sdlrenderer', ['imgui_impl_sdlrenderer.*'],
                Both(HasInclude('<SDL.h>'), IsDefined('__BPT_DETECTED_SDL_V2_0_17'))),
    BackendInfo('vulkan', ['imgui_impl_vulkan.*'], HasInclude('<vulkan/vulkan.h>')),
    BackendInfo('wgpu', ['imgui_impl_wgpu.*'], HasInclude('<webgpu/webgpu.h>')),
    BackendInfo('win32', ['imgui_impl_win32.*'], has_includes_cond('<windows.h>', '<windowsx.h>')),
]


def select_files(dir: Path, pattern: str) -> Iterable[Path]:
    return dir.glob(pattern)
    # XXX: The below check can be used to validate that patterns match anything.
    #      Files were added/removed across versions, so this should only be used
    #      to validate against a specific known ImGui version.
    found = tuple(dir.glob(pattern))
    assert found, f'No files matched pattern "{pattern}"'
    return found


inc_re = re.compile(r'#include\s+"(imgui.+)".*')
EXEMPT_FILES = ['imgui_impl_android.h', 'imgui_impl_opengl3_loader.h']


def wrap_file_cond(path: Path, content: str, cond: Condition) -> str:
    mat = inc_re.search(content)
    assert mat or path.name in EXEMPT_FILES, f'{path} does not have any #include directives?'
    if not mat:
        return content
    hdr = mat.group(1)
    assert hdr.startswith('imgui'), f'[{path}] does not #include "imgui.h" first'
    line_end = mat.end() + 1
    before = content[:line_end]
    after = content[line_end:]
    cond_str: str = cond.render()
    cond_line = f'#if {cond_str}\n'
    end = '\n#endif  // (bpt inserted conditional)\n'
    disclaimer_begin = textwrap.dedent(r'''
        /// ! NOTICE: ##########################################################
        /// The following conditional that is wrapping this file was inserted by the
        /// bpt port of the ImGui package. This condition is not part of the ImGui
        /// distribution and is not the responsibility of ImGui nor its contributors.
        ///
        /// For issues, questions, and comments related to this preprocessor check,
        /// please open an issue with bpt and the bpt ports project.
    ''')
    disclaimer_end = textwrap.dedent(r'''
        /// [END of bpt-inserted preprocessor condition] #######################

    ''')

    if path.suffix == '.h':
        cond_line = textwrap.dedent(f'''
            #if !({cond_str})
                #ifndef __BPT_IMGUI_NO_WARN
                    #ifdef _MSC_VER
                        #pragma message("warning: [Message from bpt] This ImGui backend is not usable on the current toolchain/platform/build configuration")
                    #else
                        #pragma GCC warning "[Message from bpt] This ImGui backend is not usable on the current toolchain/platform/build configuration"
                    #endif
                #endif
            #else
                #define __BPT_BACKEND_OKAY
            #endif
        ''')
        end = textwrap.dedent('''
            #ifdef __BPT_BACKEND_OKAY
            #undef __BPT_BACKEND_OKAY
            #endif
        ''')
    else:
        before = f'#define __BPT_IMGUI_NO_WARN\n' + before
    if path.stem.endswith('sdlrenderer'):
        # SPECIAL CASE: The check for SDLRenderer requires insepcting an SDL macro
        disclaimer_begin += textwrap.dedent('''
            #if __has_include(<SDL.h>)
                #include <SDL.h>
                #if SDL_VERSION_ATLEAST(2,0,17)
                    #define __BPT_DETECTED_SDL_V2_0_17 1
                #endif
            #endif
        ''')
    if path.name == 'imgui_impl_vulkan.h':
        # SPECIAL CASE: The Vulkan backend header tries to #include vulkan, but
        # we don't want it to do that unless it actually will succeed.
        cond_line += '#ifdef __BPT_BACKEND_OKAY\n'
        after += '#endif  // __BPT_BACKEND_OKAY\n'

    return before + disclaimer_begin + cond_line + disclaimer_end + after + end


async def fixup_backend(root: Path, src_dir: Path, backend: BackendInfo) -> None:
    be_dir = root / 'backends'
    files = tuple(itertools.chain.from_iterable(select_files(be_dir, pat) for pat in backend.patterns))
    for f in files:
        relpath = f.relative_to(be_dir)
        content = f.read_text('utf-8')
        if backend.condition is not None:
            content = wrap_file_cond(f, content, backend.condition)
        src_dir.joinpath(relpath).write_text(content)


async def fixup_clone(root: Path, version: VersionInfo, rev: int) -> None:
    src_dir = root / 'src'
    await fs.move_files(into=src_dir,
                        files=itertools.chain(
                            root.glob('imgui*.h'),
                            root.glob('imgui*.cpp'),
                            root.glob('imstb*.h'),
                            root.glob('imstb*.cpp'),
                            [root / 'imconfig.h'],
                        ),
                        whence=root)
    config_h = src_dir / 'imconfig.h'
    config_content = config_h.read_text('utf-8')
    new_content = config_content.replace('#pragma once', CONFIG_INCLUDE_TWEAKS)
    config_h.write_bytes(new_content.encode('utf-8'))
    for inf in backends:
        await fixup_backend(root, src_dir, inf)
    # yapf: disable
    crs.write_crs_file(root, {
        'name': 'imgui',
        'version': str(version),
        'pkg-version': rev,
        'schema-version': 0,
        'libraries': [{
            'name': 'imgui',
            'path': '.',
            'dependencies': [],
            'test-dependencies': [],
            'using': [],
            'test-using': [],
        }],
    })
    # yapf: enable


class ImGuiPort(git.SimpleGitPort):
    async def prepare(self, clone: Path) -> Path:
        await fixup_clone(clone, self.package_id.version, self.package_id.revision)
        return clone


def port_for_tag(tag: str, major: int, minor: int, patch: int) -> ImGuiPort:
    return ImGuiPort(
        'imgui',
        port.PackageID('imgui', VersionInfo(major, minor, patch), IMGUI_PORT_REVISION),
        github.gh_repo_url('ocornut', 'imgui'),
        tag,
    )


def ports_for_tags(tags: Iterable[str]) -> port.PortIter:
    pat = re.compile(r'v(\d+)\.(\d+)(?:\.(\w+))?$')
    for tag in tags:
        mat = pat.match(tag)
        if mat is None:
            continue
        maj, min_, patch = mat.groups()
        yield port_for_tag(tag, int(maj), int(min_), int(patch) if patch else 0)


async def all_ports() -> port.PortIter:
    tags = await github.get_repo_tags('ocornut', 'imgui')
    return ports_for_tags(tags)
