"""Fill one draft Playlist card from YouTube Music. Install ytmusicapi for live lookup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
from urllib.parse import quote, urlsplit
from urllib.request import urlopen


def normalized(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def resolve(client, title, artist, album=None):
    hits = client.search(f"{title} {artist}", filter="songs", limit=30)
    editions = {}
    for hit in hits:
        credit = ", ".join(a["name"] for a in hit.get("artists") or [])
        release = hit.get("album") or {}
        if (normalized(hit.get("title", "")) == normalized(title)
                and normalized(credit) == normalized(artist) and release.get("id")
                and (not album or normalized(release["name"]) == normalized(album)
                     or release["id"] == album)):
            editions[release["id"]] = (hit["title"], credit, release["name"])
    details = {}
    if not editions:
        # Some regional catalogues expose album results even when Songs is empty.
        query = title if not album or album.startswith("MPRE") else album
        for hit in client.search(f"{query} {artist}", filter="albums", limit=20):
            album_id = hit.get("browseId")
            credits = ", ".join(a["name"] for a in hit.get("artists") or [])
            if not album_id or normalized(credits) != normalized(artist):
                continue
            if album and normalized(hit["title"]) != normalized(album) and album_id != album:
                continue
            detail = client.get_album(album_id)
            for track in detail.get("tracks") or []:
                credit = ", ".join(a["name"] for a in track.get("artists") or [])
                if normalized(track["title"]) == normalized(title) and normalized(credit) == normalized(artist):
                    editions[album_id] = (track["title"], credit, detail["title"])
                    details[album_id] = detail
    if len(editions) != 1:
        choices = ", ".join(f"{value[2]} ({key})" for key, value in editions.items())
        raise ValueError("앨범을 하나로 확인할 수 없습니다. " +
                         ("--album으로 판본을 선택하세요. " + choices if choices else "곡명과 전체 아티스트 표기를 확인하세요."))
    album_id, (title, artist, _) = next(iter(editions.items()))
    detail = details.get(album_id) or client.get_album(album_id)
    year = str(detail.get("year") or "")
    covers = [c for c in detail.get("thumbnails") or []
              if c.get("width") and c.get("width") == c.get("height")
              and urlsplit(c["url"]).scheme == "https"]
    if not re.fullmatch(r"[0-9]{4}", year) or not covers:
        raise ValueError("선택한 앨범에서 발매연도 또는 정사각 앨범아트를 확인할 수 없습니다.")
    return dict(title=title, artist=artist, year=year, album=detail["title"],
                locator="https://music.youtube.com/browse/" + quote(album_id, safe=""),
                artwork_url=max(covers, key=lambda c: c["width"])["url"])


def save_atomic(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
            f.close()
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


def fetch_cover(url):
    with urlopen(url, timeout=25) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("앨범아트 크기가 16MB를 초과합니다.")
    if data.startswith(b"\xff\xd8\xff"):
        return data, "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data, "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return data, "webp"
    raise ValueError("앨범아트 응답이 이미지 파일이 아닙니다.")


def fill(path, page_id, title, artist, album, client, download=fetch_cover):
    job = json.loads(path.read_text())
    if job.get("category") != "playlist" or job.get("state") != "draft":
        raise ValueError("Playlist 초안에서 실행하세요.")
    pages = [p for p in job["pages"] if p["id"] == page_id and p["pattern"] == "track-list"]
    if len(pages) != 1 or len(pages[0].get("items", [])) != 1:
        raise ValueError("곡마다 별도 track-list 페이지를 준비하고 페이지 ID를 지정하세요.")
    record = resolve(client, title, artist, album)
    data, ext = download(record["artwork_url"])
    relative = Path("artwork") / (hashlib.sha256(data).hexdigest() + "." + ext)
    file = path.parent / relative
    file.parent.mkdir(exist_ok=True)
    save_atomic(file, data)
    source_id = "ytmusic-" + hashlib.sha256(record["locator"].encode()).hexdigest()[:16]
    source = dict(id=source_id, locator=record["locator"], artwork_url=record["artwork_url"], checked=True)
    job["sources"] = [s for s in job.get("sources", []) if s["id"] != source_id] + [source]
    if source_id not in job.setdefault("source_ids", []):
        job["source_ids"].append(source_id)
    pages[0]["items"] = [dict(kind="track-row", title=record["title"],
        meta=f"{record['artist']} · {record['year']}", artist=record["artist"],
        release_year=record["year"], album=record["album"], source_id=source_id,
        artwork_ref=relative.as_posix())]
    pages[0].pop("render", None)
    for group in ("approvals", "qa"):
        job[group] = dict.fromkeys(job.get(group, {}), False)
    save_atomic(path, (json.dumps(job, indent=2, ensure_ascii=False) + "\n").encode())
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("job", "page", "title", "artist"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--album", help="동일 곡의 앨범명 또는 YouTube Music 앨범 ID")
    args = parser.parse_args()
    try:
        from ytmusicapi import YTMusic
    except ImportError:
        sys.exit("Playlist 가상환경에 ytmusicapi를 설치하세요. README의 실행 예시를 참고하세요.")
    try:
        record = fill(Path(args.job), args.page, args.title, args.artist, args.album, YTMusic())
    except Exception as exc:
        sys.exit(f"곡 카드 확인 대기 · {exc}")
    print(f"{record['title']} / {record['artist']} / {record['year']}\n{record['locator']}")


if __name__ == "__main__":
    main()
