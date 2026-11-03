"""Interactive, per-workstation Neulis Alt setup. --check is read-only."""
import argparse
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import webbrowser

FAMILY = "Neulis Alt"
STYLES = ("Regular", "Medium", "Bold")
PUBLISHER = "https://ladd-design.com/family/neulis/"
PERSONAL = "https://befonts.com/neulis-font-family.html"

# Download button published on the personal-use page. Browser handles the download.
PERSONAL_DOWNLOAD = "https://befonts.com/downfile/b3f5d207f6022f9e487c163a48537eec.1088986"

MAC_QUERY = """
ObjC.import('AppKit');
var manager = $.NSFontManager.sharedFontManager;
if (!Number(manager.availableFontFamilies.count)) throw Error('Empty font catalog');
var faces = ObjC.deepUnwrap(manager.availableMembersOfFontFamily('Neulis Alt')) || [];
JSON.stringify(faces.map(function(face) { return face[1]; }));
"""
WIN_QUERY = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore
$families = [Windows.Media.Fonts]::SystemFontFamilies
if (!$families.Count) { throw 'Empty font catalog' }
$styles = foreach ($family in $families) {
    foreach ($face in $family.GetTypefaces()) {
        $glyph = $null
        if (!$face.TryGetGlyphTypeface([ref]$glyph)) { continue }
        if ($glyph.FamilyNames.Values -contains 'Neulis Alt') {
            $glyph.FaceNames.Values | Where-Object { $_ -in @('Regular','Medium','Bold') }
        }
    }
}
ConvertTo-Json -InputObject @($styles) -Compress
"""


def missing_styles(system):
    if system == "Darwin":
        cmd = ["/usr/bin/osascript", "-l", "JavaScript", "-e", MAC_QUERY]
    elif system == "Windows":
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", WIN_QUERY]
    else:
        raise ValueError("이 도구는 macOS와 Windows 데스크톱에서 실행하세요.")
    result = subprocess.run(cmd, capture_output=True, check=True, timeout=90)
    found = json.loads(result.stdout.decode("utf-8-sig"))
    if not isinstance(found, list):
        raise ValueError("OS 글꼴 목록을 확인하지 못했습니다.")
    return [style for style in STYLES if style not in found]


def file_style(path):
    """Read English OpenType name records from static desktop fonts."""
    if path.suffix.lower() not in (".otf", ".ttf") or path.stat().st_size > 32_000_000:
        return None
    with path.open("rb") as font:
        header = font.read(12)
        if len(header) < 12 or header[:4] not in (b"OTTO", b"\x00\x01\x00\x00"):
            return None
        count = struct.unpack_from(">H", header, 4)[0]
        for tag, _, offset, size in struct.iter_unpack(">4sIII", font.read(16 * count)):
            if tag == b"name" and 6 <= size <= 1_000_000:
                font.seek(offset)
                table = font.read(size)
                break
        else:
            return None
    _, count, strings = struct.unpack_from(">HHH", table)
    names = {}
    for pid, enc, lang, key, length, start in struct.iter_unpack(">6H", table[6:6 + 12 * count]):
        if key not in (1, 2, 16, 17):
            continue
        if pid == 3 and enc in (1, 10) and lang == 0x409:
            codec = "utf-16-be"
        elif (pid, enc, lang) == (1, 0, 0):
            codec = "mac_roman"
        else:
            continue
        names[key] = table[strings + start:strings + start + length].decode(codec)
    if names.get(16, names.get(1)) == FAMILY:
        return names.get(17, names.get(2))
    return None


def setup(check_only=False):
    system = platform.system()
    missing = missing_styles(system)
    if not missing:
        print("Neulis Alt 세 굵기를 OS에서 확인했습니다. 제작 전 Figma에서도 로드를 확인하세요.")
        return 0
    print("OS에서 확인되지 않은 Neulis Alt 굵기:", ", ".join(missing))
    if check_only or not sys.stdin.isatty():
        return 1
    print("1 라이선스가 있는 로컬 파일 설치  /  2 제작사 다운로드 페이지 열기")
    print("3 개인용 테스트에 한해 BeFonts 다운로드 요청  /  Enter 건너뛰기")
    choice = input("선택: ").strip()
    if choice not in ("1", "2", "3"):
        return 1
    if choice in ("2", "3"):
        url = PUBLISHER if choice == "2" else PERSONAL_DOWNLOAD
        if choice == "3":
            print("개인용 다운로드 주소가 바뀌었으면 원본 페이지를 이용하세요:", PERSONAL)
        print(url)
        webbrowser.open(url)
        print("사용 조건을 확인하고 파일을 받아 압축을 풀어 주세요. 기존 Figma 문서는 Neulis Alt가 필요합니다.")
    directory = input("OTF/TTF가 있는 폴더 경로 (Enter 건너뛰기): ").strip().strip('"')
    if not directory:
        return 1
    folder = Path(directory).expanduser()
    if not folder.is_dir():
        raise ValueError("지정한 폴더를 열 수 없습니다.")
    selected = {}
    for path in sorted(folder.iterdir()):
        if not path.is_symlink() and path.is_file():
            try:
                style = file_style(path)
            except (OSError, struct.error, UnicodeError):
                continue
            if style in missing:
                if style in selected:
                    raise ValueError(f"{style} 파일이 여러 개입니다. 사용할 버전만 골라 별도 폴더에 넣어 주세요.")
                selected[style] = path.resolve()
    if not selected:
        print("필요한 Neulis Alt 굵기와 내부 이름이 일치하는 파일이 없습니다.")
        return 1
    for style, path in selected.items():
        print(f"{style}  {path}")
    if input("위 파일을 이 용도로 사용할 권한이 있고 현재 사용자용 설치 창을 열까요? [y/N] ").strip().lower() != "y":
        return 1
    for path in selected.values():
        if system == "Darwin":
            subprocess.run(["/usr/bin/open", "-a", "Font Book", str(path)], check=True)
        else:
            os.startfile(str(path))
    input("OS 설치 창에서 현재 사용자용 설치를 마치고 Enter를 누르세요: ")
    return setup(check_only=True)


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="확인만 하고 종료")
    try:
        sys.exit(setup(parser.parse_args().check))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"폰트 확인 또는 설치 창 열기 실패: {error}", file=sys.stderr)
        sys.exit(2)
    except (EOFError, KeyboardInterrupt):
        sys.exit(1)
