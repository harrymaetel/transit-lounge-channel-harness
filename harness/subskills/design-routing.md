# 디자인 라우팅

필요한 역할만 순서대로 적용한다: 다빈치(내용·순서) → 몬드리안(배치) → 라인(구분·연결) → 모네(색·사진) → 추사(타이포) → 안목(가독성).

1. references/page-patterns.md와 선택 카테고리의 기준 흐름을 읽는다. references/pattern-catalog.json에서 페이지별 pattern과 슬롯을 선택한다.
2. 현재 Figma의 카테고리·시안·역할 프레임을 확인한다. 사용자 수정 이후라면 오래된 노드 ID보다 최신 이름·내용·구조를 우선해 다시 찾는다.
3. references/font-workflow.md에 따라 Neulis Alt 사용 가능 여부를 먼저 검사한다. family와 굵기를 보존한다.
4. 콘텐츠 첫 문장은 Title, 주요 내용은 Body 또는 Items, 하단 출처·안내는 Support로 분리한다. 브랜드 헤더와 로고는 별도다.
5. 대상은 audience-pills, 순서 활동은 numbered-pills, 음악은 album-track-rows. references/element-patterns.md의 독립 프레임·이미지·텍스트 스택을 유지한다. 문단 하나로 대체하지 않는다.
6. 초과 항목·원고는 같은 역할의 다음 페이지로 옮긴다. 장수는 고정하지 않는다.
7. 실제 텍스트 노드와 반복 요소를 검사하고 job.pages[].render에 근거를 기록한다. 자동 글자 수 검사를 시각 QA로 간주하지 않는다.

8. 실제 제작 전 references/figma-production.md의 네이티브 API·원본 보호·TEXT 부모 분기를 적용한다. 이전 runs의 보정 스크립트를 통째로 재실행하지 않는다.
9. references/render-evidence.md에 따라 전체 텍스트 목록과 역할 ID를 다시 수집한다. 표지 숨김 문구·카테고리 헤더·고정 포스터·사진 대비 보정을 완료한 후 해당 페이지를 재검수한다.
