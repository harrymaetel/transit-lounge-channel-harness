# 작업 계약 v1.2

새 캐러셀은 schema_version 1.2을 쓴다. 1.0 기본 작업 필드는 호환되지만 copy_ready 이후의 캐러셀은 pages가 필요하다. 작업 하나는 시안 한 세트이며 여러 시안은 별도 job으로 검사한다.

기본 필드: job_id, channel, category, state, objective, audience, message, source_ids, sources, deliverables, approvals, qa. 전체 예시는 [event-job.json](../examples/event-job.json), 곡 행 예시는 [playlist-job.json](../examples/playlist-job.json)을 본다.

## pages

```json
{
  "id": "p04",
  "role": "Who-For",
  "pattern": "audience-cards",
  "content": {
    "eyebrow": "추천 대상",
    "title": "이런 분과 함께해요",
    "support": "처음 오시는 분도 환영해요"
  },
  "items": [
    {"kind": "audience-pill", "text": "기록을 시작하고 싶은 분"},
    {"kind": "audience-pill", "text": "나만의 방식을 찾는 분"}
  ]
}
```

- pattern은 해당 카테고리의 pattern-catalog.json 목록에서 선택한다. role은 프레임 명명·편집 목적에 쓴다.
- content는 해당 패턴의 slots만 허용한다. 빈 선택 슬롯은 생략한다.
- asset_ref는 표지·사진 카드의 실제 작업 자산 참조다. 초안 플레이스홀더는 발행 전 교체·권리 검수한다.
- 프로그램 항목: kind=program-pill, order=1부터 연속, text는 번호를 제외한 원고. 표시 번호는 검사가 더해 센다.
- 곡 항목: kind=track-row, artwork_ref, title, meta(아티스트 · 연도). design_ready부터 artist, release_year(네 자리 문자열), album, 검증된 source_id, 실제 artwork_ref가 필요하다. 다른 패턴의 항목과 섞지 않는다.
- 곡 카드는 페이지당 1개, 추천·프로그램은 페이지당 최대 3개. 초과하면 페이지를 늘린다. deliverables[].cards는 실제 pages 길이와 일치해야 한다. 기준안 장수를 강제하지 않는다.
- 원고 상한은 catalog의 max_chars/max_lines. 원고의 줄 수 검사는 자동 줄바꿈을 추측하지 않는다.

## design_ready 이후 render 근거

모든 페이지에 render가 필요하다. 실제 Figma/렌더러를 검사한 결과만 기록한다. 아래는 형식 설명용으로, 검사 결과로 재사용하지 않는다.

```json
{
  "node_id": "actual-frame-id",
  "inspected_at": "actual-inspection-time",
  "evidence": "actual-screenshot-or-inspection-record",
  "layout": "audience-pills",
  "overflow": false,
  "font_runs": [
    {"family": "Neulis Alt", "style": "Regular"},
    {"family": "Neulis Alt", "style": "Bold"},
    {"family": "Neulis Alt", "style": "Medium"}
  ],
  "slots": {
    "title": {"node_id": "actual-title-id", "lines": 1, "family": "Neulis Alt", "style": "Bold", "overflow": false},
    "items.0.text": {"node_id": "actual-item-text-id", "lines": 1, "family": "Neulis Alt", "style": "Medium", "overflow": false}
  },
  "elements": [
    {"kind": "audience-pill", "container_node_id": "actual-item-container-id"}
  ]
}
```

slots에는 사용한 eyebrow/title/body/support 및 모든 items.N.field를 빠짐없이 기록한다. 각 텍스트 node_id와 항목 container_node_id는 중복되지 않아야 한다. font_runs는 헤더를 포함한 페이지 전체 텍스트의 폰트 범위를 검사한 결과다. elements는 반복 요소가 있을 때 항목마다 하나씩 필요하다. 이미지·텍스트가 실제로 구성됐는지는 시각 QA가 함께 확인한다.

qa는 structural/content/visual/release 외에 캐러셀의 typography/element_layout 두 항목을 포함한다. 사용자 content/design/publish 승인과 이 QA를 모두 갖춰야 check-ready가 통과한다. 이 검사기는 보고된 근거를 검사하며 실제 Figma 렌더를 대신하지 않는다.

## 상태와 근거

카테고리: event, playlist, link-mingle, interview, moments, lines, other. other는 분류 전 초안이며 확정 카테고리/패턴이 생긴 뒤 제작한다.

상태 순서는 AGENTS.md를 따른다. user_approved는 실제 사용자가 결과를 승인했을 때만 기록한다. published는 실제 외부 발행 확인이 있을 때만 기록한다. 승인·QA 값을 예시에서 그대로 복사하지 않는다.

## v1.2 추가 계약

위 render 예시는 기본 필드 설명이다. 새 작업은 [render-evidence.md](render-evidence.md)의 실측 필드를 함께 기록해야 한다. 포스터 원고는 poster_content, 역할별 한도는 catalog.artwork_slots를 사용한다. 구버전 기록은 보존하되 check-ready에는 current_render_contract가 필요하다.

## Event 공통 장소 페이지

`venue-guide`의 content는 카탈로그 `fixed_content`와 일치해야 하고 지도 `asset_ref`가 필요하다. 새 Event 초안은 `event-job.json`의 7장 구성을 기준으로 한다. 장소 정보는 `venue-guide.venue`에서 가져온다. 제작 시 지도 자산과 역할별 실측 근거를 연결한다. [세부 규칙](event-venue.md)
