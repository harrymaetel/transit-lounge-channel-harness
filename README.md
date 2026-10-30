# 트랜짓 라운지 채널 운영 하네스

버전 **0.3**. 트랜짓 라운지의 기획 → 카피 → 디자인 → QA → 사용자 승인 → 발행 준비 → 분석 → Levelup을 관리합니다. Event, Playlist, Link & Mingle, Interview, Moments, Lines의 페이지 패턴을 조건부로 불러옵니다.

## 시작하기

Python 3.9 이상으로 저장소 루트에서 실행합니다. 검사기는 외부 패키지가 필요하지 않습니다.

```sh
python3 harness/scripts/harness.py route --job harness/examples/event-job.json
python3 harness/scripts/harness.py validate --job harness/examples/event-job.json
python3 harness/scripts/harness.py check-ready --job harness/examples/event-job.json
```

예제는 승인 전 초안이므로 `validate`는 통과하지만 `check-ready`는 실패하는 것이 정상입니다. 에이전트는 [AGENTS.md](AGENTS.md)와 [운영 스킬](skills/run-transit-channel/SKILL.md)부터 읽습니다. 스킬을 단독 복사하면 상대 경로가 끊기므로 저장소 구조를 유지하세요.

## 제작·검수 기준

- **Neulis Alt 유지:** Regular/Medium/Bold의 실제 로드를 확인합니다. 원격 환경에서 사용할 수 없으면 폰트가 설치된 Figma 데스크톱에서 작업합니다. 대체 폰트 자동 치환은 금지합니다.
- **레이아웃 유지:** 제목 → 주요 내용 → 보조문구를 분리합니다. 추천 대상은 둥근 카드, 프로그램은 번호 카드, 곡 순서는 앨범 이미지와 메타 정보가 있는 행으로 만듭니다. 헤더·로고·원본은 보호합니다.
- **글자 수와 실제 줄 수:** NFC 기준으로 공백과 부호를 포함해 계산합니다. 줄바꿈은 글자 수에서 제외하고 빈 줄은 줄 수에 포함합니다. 프로그램 번호도 예산에 포함합니다. 실제 폰트·행간·HEIGHT·노드 높이와 원고 일치를 대조합니다.
- **초과 시 페이지 추가:** 글씨를 줄이거나 말줄임으로 맞추지 않습니다. 슬롯 한도와 전체 콘텐츠 높이 860px를 함께 확인합니다. 카테고리별 기본 장수는 상한이 아닙니다.
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
