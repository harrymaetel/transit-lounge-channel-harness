# Transit Playlist

기준 흐름: 표지 → 분위기 → 곡 순서 → 감상 질문 → 재생 CTA. 기준 장수는 제한이 아니다.

Listening-Flow는 track-list다. 선곡 순서대로 곡마다 한 페이지를 배정한다. 곡명과 아티스트를 받으면 README의 playlist_lookup.py를 해당 작업 초안에서 실행한다. 선택한 앨범의 표지·곡명·아티스트·발매연도를 채우고 album-track-rows 원본을 복제한다. 판본이 여럿일 때만 선택을 요청한다. 곡명과 앨범아트의 대응 및 재생 링크를 확인한다. Listening-Prompt는 질문 제목과 감상 본문을 나눈다.

references/page-patterns.md의 해당 카테고리 관찰값과 references/pattern-catalog.json의 슬롯별 운영 상한을 적용한다. Neulis Alt와 제목→주요 내용→보조 위계를 유지한다.

## 제작 전에 받을 내용

1. 언제, 어떤 분위기에서 들을 플레이리스트인가요?
2. 곡을 재생 순서대로 적어 주세요. 곡마다 곡명과 아티스트를 알려 주세요.
3. 특히 귀 기울였으면 하는 곡이나 구간이 있나요?
4. 전체 목록을 들을 수 있는 링크가 있나요?
