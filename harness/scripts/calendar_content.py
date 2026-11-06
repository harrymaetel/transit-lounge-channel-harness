"""Build a monthly Calendar carousel from one event list, using local date rules."""
import argparse
import calendar
from copy import deepcopy
from datetime import date, time
import json
from pathlib import Path
import re
import unicodedata

WEEKDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
ROOT = Path(__file__).resolve().parents[1]


def parse_lines(text, year, month):
    events = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*(\d{1,2})/(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2}:\d{2})\s*[–—-]\s*(\d{2}:\d{2})\s*:\s*(.+?)\s*', line)
        if not match:
            raise ValueError('일정 형식을 확인하세요. MM/DD FRI HH:MM – HH:MM : 행사명')
        m, d, weekday, start, end, title = match.groups()
        day = date(year, int(m), int(d))
        if day.month != month or weekday.upper() != WEEKDAYS[day.weekday()]:
            raise ValueError('입력한 월 또는 요일이 날짜와 다릅니다. ' + line)
        events.append(dict(id=f'event-{len(events)+1:02}', date=day.isoformat(),
                           start=start, end=end, title=title, image_kind='none'))
    return events


def normalize_events(data, max_title):
    year, month = data.get('year'), data.get('month')
    if type(year) is not int or type(month) is not int:
        raise ValueError('대상 연도와 월을 정수로 입력하세요.')
    date(year, month, 1)
    events = data.get('events')
    if not isinstance(events, list) or not events:
        raise ValueError('월별 행사 목록이 필요합니다.')
    result, ids = [], set()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or not event['id'] or event['id'] in ids:
            raise ValueError('행사별 고유 ID가 필요합니다.')
        ids.add(event['id'])
        day = date.fromisoformat(event['date'])
        if (day.year, day.month) != (year, month):
            raise ValueError('대상 월 밖의 행사입니다. ' + event['id'])
        if event.get('all_day') is True:
            period = 'ALL DAY'
        else:
            start, end = event['start'], event['end']
            if not all(isinstance(t, str) and re.fullmatch(r'\d{2}:\d{2}', t) for t in (start, end)) or time.fromisoformat(end) <= time.fromisoformat(start):
                raise ValueError('시작·종료 시간을 HH:MM으로 확인하세요. ' + event['id'])
            period = f'{start} – {end}'
        title = event.get('title')
        if not isinstance(title, str) or not title.strip() or '\n' in title:
            raise ValueError('행사명은 한 줄로 입력하세요.')
        short = event.get('short_title', title)
        if not isinstance(short, str) or not short.strip() or '\n' in short:
            raise ValueError('짧은 행사명은 한 줄로 입력하세요.')
        if len(unicodedata.normalize('NFC', short)) > max_title:
            raise ValueError(f'행사명 축약 확인이 필요합니다. {event["id"]} · {max_title}자 이내 제안 후 사용자에게 한 번 문의하세요.')
        if short != title and event.get('short_title_approved') is not True:
            raise ValueError('축약한 행사명의 사용자 승인이 필요합니다. ' + event['id'])
        image_kind = event.get('image_kind', 'none')
        if image_kind not in ('none', 'portrait', 'photo', 'poster'):
            raise ValueError('행사 이미지 유형을 확인하세요.')
        layout = event.get('detail_layout', 'text' if image_kind == 'none' else 'poster' if image_kind == 'poster' else 'photo')
        if layout not in ('text', 'photo', 'poster') or (layout == 'text') != (image_kind == 'none'):
            raise ValueError('사진 유무에 맞는 행사 상세 형식을 선택하세요.')
        if image_kind != 'none' and not event.get('asset_ref'):
            raise ValueError('행사 이미지 파일을 연결하세요. ' + event['id'])
        if 'featured' in event and type(event['featured']) is not bool:
            raise ValueError('featured는 true 또는 false여야 합니다.')
        result.append(dict(event, short_title=short, detail_layout=layout,
                           schedule=f'{day.month:02}/{day.day:02} {WEEKDAYS[day.weekday()]} {period}'))
    return sorted(result, key=lambda e: (e['date'], e.get('start', ''), e['id']))


def build_pages(data, rules):
    config = rules['calendar']
    events = normalize_events(data, config['short_title_max_chars'])
    year, month = data['year'], data['month']
    cover = data.get('cover_asset_ref')
    if not isinstance(cover, str) or not cover.strip():
        raise ValueError('1페이지 표지 이미지를 사용자에게 요청하세요.')
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    cells = [dict(day=d, event_ids=[e['id'] for e in events if int(e['date'][-2:]) == d] if d else [])
             for week in weeks for d in week]
    pages = [dict(role='Cover-Image', pattern='calendar-cover', asset_ref=cover,
                  content=dict(title=f'{month}월 행사 안내'))]
    limit = config['agenda_items_per_page']
    for i in range(0, len(events), limit):
        batch = events[i:i+limit]
        pages.append(dict(role='Month-Overview', pattern='calendar-overview',
                          content=dict(year=str(year), month=MONTHS[month], month_number=str(month)),
                          grid=dict(weekdays=['SUN']+WEEKDAYS[:6], cells=deepcopy(cells),
                                    row_height=min(120, 600/len(weeks))),
                          items=[dict(kind='calendar-event', event_id=e['id'], schedule=e['schedule'], title=e['short_title']) for e in batch]))
    for event in events:
        if event.get('featured', True) is False:
            continue
        layout = event['detail_layout']
        page = dict(role='Event-'+layout.title(), pattern='calendar-event-'+layout, event_id=event['id'], month_label=f'{month}월 행사 안내',
                    content=dict(title=event['short_title'], body=event['schedule'],
                                 support=event.get('support', '참가 안내 확인 후 입력')))
        if event.get('support') == '':
            page['content'].pop('support', None)
        if layout != 'text':
            page['asset_ref'] = event['asset_ref']
        if layout == 'poster':
            page['content'] = {}
        pages.append(page)
    pages.append(dict(role='CTA', pattern='cta', content=dict(
        title='이번 달, 트랜짓 라운지에서 만나요', body='관심 있는 행사의 일정과\n신청 방법을 확인해 주세요.',
        support=data.get('cta_text', '신청 경로 확인 후 입력'))))
    if 'cta_content' in data:
        pages[-1]['content'] = deepcopy(data['cta_content'])
    for i, page in enumerate(pages, 1):
        page['id'] = f'p{i:02}'
    return pages


def validate_calendar(job, rules):
    try:
        expected = build_pages(job.get('calendar', {}), rules)
    except (ValueError, KeyError, TypeError) as exc:
        return ['calendar:' + str(exc)]
    pages = job.get('pages')
    if not isinstance(pages, list) or len(pages) != len(expected):
        return ['calendar:rebuild-pages-from-events']
    errors = []
    for page, wanted in zip(pages, expected):
        if not isinstance(page, dict) or any(page.get(k) != v for k, v in wanted.items()):
            errors.append('calendar:' + wanted['id'] + ':events-grid-list-detail-mismatch')
    if job.get('state') not in ('draft', 'classified', 'strategy_ready', 'copy_ready'):
        if not job.get('calendar', {}).get('cta_text'):
            errors.append('calendar:confirmed-cta-required')
        for event in job['calendar']['events']:
            if event.get('featured', True) and event.get('image_kind', 'none') != 'poster' and 'support' not in event:
                errors.append('calendar:confirmed-event-support-required')
        for page in pages:
            if str(page.get('asset_ref', '')).startswith('draft:'):
                errors.append('calendar:uploaded-image-required')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', required=True)
    parser.add_argument('--output', required=True, help='새 초안 경로. 기존 파일 덮어쓰기 금지')
    parser.add_argument('--lines', help='선택. 일정 텍스트 파일. 기존 events가 비어 있을 때만 사용')
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding='utf-8'))
    if job.get('category') != 'calendar' or job.get('state') != 'draft':
        raise ValueError('Calendar 초안에서 실행하세요.')
    if args.lines:
        if job['calendar'].get('events'):
            raise ValueError('기존 행사 자료를 보존하려면 새 입력 초안에서 --lines를 사용하세요.')
        job['calendar']['events'] = parse_lines(Path(args.lines).read_text(encoding='utf-8'), job['calendar']['year'], job['calendar']['month'])
    rules = json.loads((ROOT/'references/pattern-catalog.json').read_text(encoding='utf-8'))
    job['pages'] = build_pages(job['calendar'], rules)
    for d in job['deliverables']:
        if d.get('kind') == 'carousel':
            d['cards'] = len(job['pages'])
    for group in ('qa', 'approvals'):
        job[group] = dict.fromkeys(job.get(group, {}), False)
    output = Path(args.output)
    with output.open('x', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'{len(job["pages"])} pages written to {output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit(str(exc))
