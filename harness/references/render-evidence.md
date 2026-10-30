# 실측 렌더 계약 · schema 1.2

새 캐러셀은 1.2로 만든다. 1.0/1.1은 과거 기록 읽기용이며 check-ready에서 신규 렌더 계약 게이트를 통과하지 못한다. 과거에 없던 측정값을 채워 넣지 말고 실제 재검수해야 한다.

## 수집 → 대조 → 화면 검사

1. Neulis Alt Regular/Medium/Bold의 실제 로드를 확인한다. 데스크톱과 원격은 다른 환경이다.
2. 카드 안의 **전체 텍스트**와 각 혼합 범위를 수집한다. 헤더까지 포함한 수, TEXT ID, 실제 characters, effective visibility, missing font, 클리핑, bounds를 기록한다.
3. 원고와 렌더 텍스트를 NFC/개행 정규화 후 대조한다. 글자 수는 공백·부호 포함, CR/LF 제외. 프로그램 번호도 포함한다.
4. 텍스트는 HEIGHT, 문단 간격 0, 균일한 크기·행간일 때만 실제 높이÷행간으로 계산한다. 정수 줄과의 오차는 Figma 반올림을 고려해 1.1px 이하. 명시적 줄 수보다 적으면 실패다. NONE 고정 높이·AUTO 행간·서로 다른 크기의 혼합 범위는 이 계산으로 통과시키지 말고 지원되는 구조로 정리한 뒤 재측정한다.
5. 각 슬롯 한도와 콘텐츠 전체 높이 860px를 모두 검사한다. 폰트 크기를 줄이거나 말줄임으로 맞추지 않는다. 넘치면 문구를 다듬거나 같은 역할의 페이지를 추가한다.
6. 최종 화면에서 대비, 얼굴 가림, 사진/원고 일치, 로고 간격을 확인한다. 보정한 페이지의 측정과 화면 근거는 다시 수집한다.

## render 추가 필드

기존 node_id/inspected_at/evidence/layout/overflow/font_runs/slots/elements와 함께 다음을 기록한다. captureFrame은 시각 검사를 제외한 관찰값을 수집하는 보조 함수다. 도구 성공 자체를 QA 성공으로 해석하지 않는다.

- `canvas`: `{x:0,y:0,width:1080,height:1350}`.
- `font_check`: `{environment:"figma-desktop" 또는 "figma-remote", loaded_styles:["Regular","Medium","Bold"], missing_fonts:false, evidence:"실제 로드 근거"}`.
- `text_node_count`, `text_nodes`: 수가 일치해야 한다. 각 노드는 `node_id,text,effective_visible,missing_font,clipped,bounds,auto_resize,paragraph_spacing,font_runs`를 포함한다. bounds는 카드 기준 x/y/width/height, 각 font_run은 family/style/font_size/line_height_px다. effective_visible은 자신과 조상 모두의 visible/opacity를 확인한 값이다.
- `slots`: 실제 사용한 모든 역할과 고유 node_id. 본문의 reported lines가 실측 높이에서 얻은 값과 같아야 한다. 제목·본문·보조·목록 항목을 합치지 않는다.
- `header`: `{brand_node_id,category_node_id}`. 서로 다른 실제 노드이고 텍스트가 Transit 및 catalog.category_labels 값이어야 한다.
- `logo`: `{node_id,effective_visible,bounds}`. 보조문구와 겹치지 않는다.
- `content_bounds`: 일반 콘텐츠 카드의 실제 컨테이너 경계. 모든 콘텐츠 슬롯이 안에 들어가고 높이 예산을 지킨다.
- `elements`: 기존 kind/container_node_id에 bounds/effective_visible 추가. 항목 텍스트는 각 행 안에 배치하고 제목 → 행 → 보조 순서와 행끼리의 비중첩을 검사한다. track-row에는 artwork_node_id/artwork_visible도 추가한다.
- 편집 가능한 포스터는 `poster_bounds`, `poster_size_mode:"FIXED"`. 원고는 `page.poster_content`에 넣고 catalog.artwork_slots 한도를 적용한다. render.slots 키는 artwork.eyebrow/title/body/support다. 이미지형 포스터의 이미지 내 문자는 육안 검수한다.
- `visual_review`: `{evidence:"최종 화면 근거",contrast:true,faces_clear:true,asset_matches_copy:true,logo_clear:true}`. 해당 문제가 없음을 직접 확인한 뒤에만 true. 사진 없는 카드의 faces_clear는 해당 없음으로 확인한다.

`validate`는 제출된 근거의 내부 일관성을 검사한다. 실시간 Figma 접속이나 진위를 증명하지 않는다. 원본/스크린샷/검사 시점은 실행 기록에 보관하고, 수정된 카드의 이전 근거를 그대로 복사하지 않는다.
