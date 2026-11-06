"""Calendar regressions. Dates and geometry below are synthetic test fixtures."""
from copy import deepcopy
from datetime import date
import unittest
from test_harness import MODULE, sample
from test_render_contract import strict_job
from calendar_content import build_pages, parse_lines, validate_calendar

RULES = MODULE.catalog()

class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.job = sample('calendar')
        self.data = self.job['calendar']

    def test_example_route_and_contract(self):
        self.assertEqual(MODULE.validate(self.job), [])
        self.assertFalse(MODULE.readiness(self.job)['ready'])
        route=MODULE.route(self.job)
        self.assertFalse(route['use_jev'])
        self.assertIn('references/calendar-workflow.md',route['load_sequence'])
        for path in route['load_sequence']:
            self.assertTrue((MODULE.ROOT/path).is_file(),path)

    def test_line_parser_checks_actual_weekday_and_month(self):
        line='11/13 FRI 19:30 – 22:00 : 북토크 워크숍'
        self.assertEqual(parse_lines(line,2026,11)[0]['date'],'2026-11-13')
        for text in (line.replace('FRI','MON'),line.replace('11/13','12/13')):
            with self.assertRaises(ValueError): parse_lines(text,2026,11)

    def test_leap_year_and_six_week_month(self):
        for year,month,day,week_count in [(2024,2,29,5),(2026,8,31,6),(2026,2,28,4)]:
            self.data.update(year=year,month=month,events=[dict(self.data['events'][0],date=date(year,month,day).isoformat())])
            grid=build_pages(self.data,RULES)[1]['grid']
            self.assertEqual(len(grid['cells']),week_count*7)
            self.assertEqual([c['day'] for c in grid['cells'] if c['day']],list(range(1,day+1)))
            self.assertLessEqual(grid['row_height']*week_count,600)
            index=next(i for i,c in enumerate(grid['cells']) if c['day']==1)
            self.assertEqual(index,(date(year,month,1).weekday()+1)%7)

    def test_same_date_preserves_every_event_and_one_highlight(self):
        self.data['events'][1]['date']=self.data['events'][0]['date']
        pages=build_pages(self.data,RULES)
        cell=next(c for c in pages[1]['grid']['cells'] if c['day']==13)
        self.assertEqual(set(cell['event_ids']),{'book','mingle'})
        self.assertEqual(sum(len(p.get('items',[])) for p in pages),3)

    def test_variants_are_alternatives_and_cta_always_last(self):
        pages=build_pages(self.data,RULES)
        self.assertEqual([p['pattern'] for p in pages[3:-1]],['calendar-event-text','calendar-event-photo','calendar-event-poster'])
        self.assertEqual(pages[-1]['role'],'CTA')
        self.assertEqual(len(pages),7)
        for count in (1,2,4,7):
            self.data['events']=[dict(self.data['events'][0],id=f'e{i}') for i in range(count)]
            pages=build_pages(self.data,RULES)
            self.assertEqual(len(pages),2+(count+1)//2+count)
            self.assertEqual([p['id'] for p in pages],[f'p{i:02}' for i in range(1,len(pages)+1)])

    def test_featured_filters_details_not_calendar_or_list(self):
        self.data['events'][1]['featured']=False
        pages=build_pages(self.data,RULES)
        self.assertEqual(len([p for p in pages if p.get('event_id')]),2)
        self.assertEqual(sum(len(p.get('items',[])) for p in pages),3)

    def test_cover_is_required_even_without_event_images(self):
        del self.data['cover_asset_ref']
        with self.assertRaisesRegex(ValueError,'표지'): build_pages(self.data,RULES)

    def test_long_title_requires_approved_short_title(self):
        e=self.data['events'][0];e['title']='매우 긴 행사 안내 제목으로 세부적인 내용을 모두 표시합니다'
        with self.assertRaisesRegex(ValueError,'축약'): build_pages(self.data,RULES)
        e['short_title']='북토크 워크숍'
        with self.assertRaisesRegex(ValueError,'승인'): build_pages(self.data,RULES)
        e['short_title_approved']=True
        pages=build_pages(self.data,RULES)
        self.assertEqual(pages[1]['items'][0]['title'],e['short_title'])
        self.assertEqual(pages[3]['content']['title'],e['short_title'])

    def test_invalid_date_time_duplicate_id_or_missing_photo_fail(self):
        for change in ({'date':'2026-11-31'},{'date':'2026-12-01'}, {'end':'18:00'}, {'start':'25:00'}, {'id':'mingle'}, {'image_kind':'portrait'}):
            data=deepcopy(self.data);data['events'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):build_pages(data,RULES)

    def test_all_day_and_optional_photo_choice(self):
        self.data['events'][0]['all_day']=True
        self.data['events'][1]['detail_layout']='poster'
        pages=build_pages(self.data,RULES)
        self.assertEqual(pages[1]['items'][0]['schedule'],'11/13 FRI ALL DAY')
        self.assertEqual(pages[4]['pattern'],'calendar-event-poster')

    def test_stale_pages_do_not_validate(self):
        for field in ('grid','items'):
            j=deepcopy(self.job);j['pages'][1][field]={}
            self.assertTrue(validate_calendar(j,RULES))
        self.data['events'][0]['title']='다른 행사'
        self.assertTrue(validate_calendar(self.job,RULES))

    def test_draft_assets_and_unconfirmed_cta_cannot_be_design_ready(self):
        self.job['state']='design_ready'
        del self.data['cta_text']
        errors=validate_calendar(self.job,RULES)
        self.assertIn('calendar:uploaded-image-required',errors)
        self.assertIn('calendar:confirmed-cta-required',errors)


def measured_grid_fixture():
    # Test the grid contract in isolation; synthetic, not a real visual review.
    page=sample('calendar')['pages'][1]
    r=strict_job()['pages'][0]['render']
    r['font_check']['loaded_styles']=RULES['patterns']['calendar-overview']['font_styles']
    r['text_nodes']=[];r['slots']={};r['calendar_grid']={'weekday_node_ids':[], 'cells':[]}
    def text(nid,value,box,style='Light'):
        return dict(node_id=nid,text=value,effective_visible=True,missing_font=False,clipped=False,bounds=box,
                    font_runs=[dict(family='Neulis Alt',style=style)])
    for i,day in enumerate(page['grid']['weekdays']):
        nid=f'w{i}';r['calendar_grid']['weekday_node_ids'].append(nid)
        r['text_nodes'].append(text(nid,day,dict(x=99+i*126,y=236,width=100,height=39),'Medium'))
    for i,c in enumerate(page['grid']['cells']):
        box=dict(x=99.428+i%7*126.857,y=275+i//7*page['grid']['row_height'],width=120,height=page['grid']['row_height'])
        nid=f'd{i}';r['text_nodes'].append(text(nid,str(c['day']) if c['day'] else '',dict(box,width=100,height=60)))
        r['calendar_grid']['cells'].append(dict(node_id=f'cell{i}',text_node_id=nid,day=c['day'],highlighted=bool(c['event_ids']),effective_visible=True,bounds=box))
    r['text_node_count']=len(r['text_nodes'])
    return page,r

class CalendarRenderTests(unittest.TestCase):
    def test_actual_date_weekday_highlight_and_geometry(self):
        page,r=measured_grid_fixture()
        check=lambda:MODULE.validate_render_evidence(page,r,{},RULES,'calendar')
        self.assertEqual(check(),[])
        for field,value,error in [('highlighted',True,'highlight'),('day',31,'mismatch'),('effective_visible',False,'mismatch')]:
            page,r=measured_grid_fixture();r['calendar_grid']['cells'][0][field]=value
            self.assertTrue(any(error in e for e in check()))
        page,r=measured_grid_fixture();r['text_nodes'][0]['text']='일'
        self.assertTrue(any('weekdays' in e for e in check()))
        page,r=measured_grid_fixture();r['calendar_grid']['cells'][0]['bounds']['x']+=120
        self.assertTrue(any('position' in e for e in check()))
        page,r=measured_grid_fixture();r['text_nodes'][7]['text']='9'
        self.assertTrue(any('mismatch' in e for e in check()))

    def test_light_italic_load_is_not_optional(self):
        page,r=measured_grid_fixture();r['font_check']['loaded_styles']=['Regular','Medium','Bold']
        self.assertTrue(any('font-check' in e for e in MODULE.validate_render_evidence(page,r,{},RULES,'calendar')))
