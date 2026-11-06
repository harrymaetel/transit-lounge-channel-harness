# 트랜짓 라운지 채널 운영 하네스

버전 **0.3**. 트랜짓 라운지의 기획 → 카피 → 디자인 → QA → 사용자 승인 → 발행 준비 → 분석 → Levelup을 관리합니다. Event, Playlist, Link & Mingle, Interview, Moments, Lines의 페이지 패턴을 조건부로 불러옵니다.

## 시작하기

브랜치·외부 기기 작업은 [관리 지침](docs/branch-management.md)을 따릅니다. [작업 요청](https://github.com/harrymaetel/transit-lounge-channel-harness/issues/new/choose)을 등록하고 [공용 운영 로그](https://github.com/harrymaetel/transit-lounge-channel-harness/issues/1)에서 변경 이력을 확인하세요. GitHub 이벤트는 자동 기록하고, 이 대화에서는 요청 시 최신 현황을 조회해 요약합니다.

새 콘텐츠를 요청하면 에이전트가 카테고리 한 가지를 선택받고, 해당 카테고리의 추가 질문과 사진 첨부를 안내합니다. 이미 알려 준 내용은 다음 요청에도 이어 씁니다. [제작 접수 절차](harness/subskills/content-intake.md)

Python 3.9 이상으로 저장소 루트에서 실행합니다. 검사기는 외부 패키지가 필요하지 않습니다.

```sh
python3 harness/scripts/harness.py route --job harness/examples/event-job.json
python3 harness/scripts/harness.py validate --job harness/examples/event-job.json
python3 harness/scripts/harness.py check-ready --job harness/examples/event-job.json
```

예제는 승인 전 초안이므로 `validate`는 통과하지만 `check-ready`는 실패하는 것이 정상입니다. 에이전트는 [AGENTS.md](AGENTS.md)와 [운영 스킬](skills/run-transit-channel/SKILL.md)부터 읽습니다. 스킬을 단독 복사하면 상대 경로가 끊기므로 저장소 구조를 유지하세요.

## Event 장소 안내

Event는 트랜짓 라운지 개최를 기본으로 합니다. 접수에서는 행사명·소개, 날짜·시간, 추천 대상, 프로그램, 참가비·신청 방법을 받습니다. 장소와 주차 안내는 공통 지도 페이지에 자동으로 채웁니다. 기본 구성은 7장이며 프로그램 다음에 장소 안내, 마지막에 신청 CTA를 둡니다. [공통 장소 안내 규칙](harness/references/event-venue.md)

## Playlist 한 곡 카드

에이전트에 “Playlist로 Ditto, NewJeans를 소개해 줘”처럼 곡명과 아티스트를 알려 주세요. 에이전트는 YouTube Music에서 음원과 앨범을 대조한 뒤 앨범아트, 정식 곡명, 아티스트, 해당 판본의 발매연도를 초안에 채웁니다. 여러 판본이 일치하면 앨범을 선택합니다.

직접 실행할 때는 Python 3.12 가상환경에서 아래 예시를 사용하세요. Windows에서는 가상환경의 python.exe로 같은 스크립트를 실행할 수 있습니다.

```sh
python -m pip install ytmusicapi==1.12.3
mkdir -p runs/my-playlist
cp harness/examples/playlist-job.json runs/my-playlist/job.json
python harness/scripts/playlist_lookup.py --job runs/my-playlist/job.json --page p03 --title "Ditto" --artist "NewJeans"
```

판본을 지정할 때는 명령 끝에 `--album "Ditto"`처럼 앨범명 또는 조회된 앨범 ID를 붙입니다. 이미지 파일은 작업 JSON 옆의 `artwork/`에, 앨범 링크와 이미지 출처는 작업 JSON에 보관합니다. Figma 제작 시 해당 파일을 이미지 채우기에 사용하고 제목·메타를 각각 별도 슬롯에 넣습니다. 여러 곡이면 Listening-Flow 페이지를 선곡 순서로 복제하고 고유 페이지 ID와 전체 카드 수를 갱신한 뒤 페이지마다 실행합니다. 기존 3곡 초안도 먼저 한 곡씩 나눕니다.

조회 실패 시 초안을 보존합니다. 공식 앨범 페이지로 직접 대조한 경우 같은 필드에 출처를 기록할 수 있습니다. 발행 전 이미지 사용 범위는 별도로 확인합니다. 조회에는 비공식 클라이언트를 사용합니다. [ytmusicapi 문서](https://ytmusicapi.readthedocs.io/en/stable/)

## 처음 설치할 때 글꼴 준비

GitHub에서 받은 저장소 폴더를 열고 Figma를 사용하는 컴퓨터에서 한 번 실행하세요. Python 3.9 이상이 필요합니다.

| macOS 터미널 | Windows PowerShell |
|---|---|
| `python3 harness/scripts/setup_fonts.py` | `py -3 harness/scripts/setup_fonts.py` |

세 굵기가 있으면 바로 끝납니다. 부족하면 **보유 파일 설치 / 제작사 페이지 열기 / 개인용 테스트 다운로드 / 건너뛰기** 중에서 고릅니다. 사용할 파일과 굵기를 확인한 뒤 OS 설치 창을 엽니다. `--check`를 붙이면 조회만 합니다. [폰트 출처와 설치 절차](harness/references/font-workflow.md)

## 제작·검수 기준

- **Neulis Alt 유지:** Regular/Medium/Bold의 실제 로드를 확인합니다. 원격 환경에서 사용할 수 없으면 폰트가 설치된 Figma 데스크톱에서 작업합니다. 대체 폰트 자동 치환은 금지합니다.
- **레이아웃 유지:** 제목 → 주요 내용 → 보조문구를 분리합니다. 추천 대상은 둥근 카드, 프로그램은 번호 카드, 곡 순서는 페이지당 앨범아트 한 장과 곡 정보가 있는 카드로 만듭니다. 헤더·로고·원본은 보호합니다.
- **글자 수와 실제 줄 수:** NFC 기준으로 공백과 부호를 포함해 계산합니다. 줄바꿈은 글자 수에서 제외하고 빈 줄은 줄 수에 포함합니다. 프로그램 번호도 예산에 포함합니다. 실제 폰트·행간·HEIGHT·노드 높이와 원고 일치를 대조합니다.
- **초과 시 페이지 추가:** 글씨를 줄이거나 말줄임으로 맞추지 않습니다. 슬롯 한도와 전체 콘텐츠 높이(기본 860px, 곡 소개 942px)를 함께 확인합니다. 카테고리별 기본 장수는 상한이 아닙니다.
- **화면 검수:** 숨김, 클리핑, 헤더 누락, 프레임 축소는 측정값으로 검사하고 대비·얼굴 가림·이미지와 내용의 일치는 최종 화면에서 확인합니다.

세부 기준은 [패턴 카탈로그](harness/references/pattern-catalog.json), [Figma 제작 규칙](harness/references/figma-production.md), [실측 렌더 계약](harness/references/render-evidence.md), [폰트 워크플로](harness/references/font-workflow.md)에 있습니다.

신규 캐러셀은 **job schema 1.2**를 사용합니다. 1.0/1.1 기록은 읽을 수 있지만 새로운 발행 준비 검수를 통과하지 못합니다. 과거 근거를 추정값으로 채워 승격하지 않습니다. 검사기는 제출된 근거의 일관성을 검사하며 실시간 Figma 검수나 사용자 승인을 대신하지 않습니다.

## 구성

| 경로 | 역할 |
|---|---|
| `harness/agents/` | 300자 이내 전문 에이전트 카드 |
| `harness/subskills/` | 상황·카테고리별 조건부 지침 |
| `harness/references/` | 브랜드·레이아웃·폰트·렌더 계약 |
| `harness/scripts/harness.py` | 로컬 라우팅, 원고·실측 근거·발행 준비 검사 |
| `harness/scripts/figma_helpers.js` | 네이티브 Figma 플러그인 제작·측정 보조 함수 |
| `harness/tests/` | 제작 오류 재발 방지 테스트 |
| `harness/decision-log.jsonl` | 사용자 확정(H)과 제안(P) 기록 |

`figma_helpers.js`는 자동 실행 플러그인이 아닙니다. 공식 Figma 스킬과 실행 환경의 API 지침을 읽은 뒤 사용합니다. 최종 한국어 카피에는 `humanize-korean`을 적용하며, 스킬이 없으면 그 사실을 기록하고 보수적인 의미 보존 검수를 수행합니다.

## 검증

Node.js 18 이상으로 네이티브 보조 함수의 회귀 테스트를 실행할 수 있습니다.

```sh
python3 -m unittest discover -s harness/tests -v
node --test harness/tests/figma_helpers.test.js
python3 harness/scripts/harness.py validate-cards
```

GitHub Actions에서도 같은 검사를 실행합니다. 테스트용 합성 측정값은 실제 Figma QA 증거가 아닙니다. [이번 제작에서 반영한 수정 사항](docs/production-lessons.md)을 참고하세요.

## 승인과 보관

`check-ready`는 실제 게시 권한을 부여하지 않습니다. 게시·예약·외부 계정 수정은 사용자 승인과 연결 도구·대상·권한 확인이 필요합니다. 브랜드 기준 변경은 사용자 확정과 Decision Log에 근거합니다.

폰트 파일·사진·비밀값·로컬 실행 기록과 일회성 Figma 수정 스크립트는 저장소에 포함하지 않습니다. 로컬 `runs/`의 과거 증거는 그대로 보관하며 새 제작에 승인값으로 복사하지 않습니다.
