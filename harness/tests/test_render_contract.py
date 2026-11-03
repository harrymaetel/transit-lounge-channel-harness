"""Synthetic geometry fixtures: these are regression tests, not Figma evidence."""
import copy
import unittest
from test_harness import MODULE, rendered_editorial


def strict_job():
    job = rendered_editorial()
    job['schema_version'] = '1.2'
    r = job['pages'][0]['render']
    r.update(canvas=dict(x=0,y=0,width=1080,height=1350),
             font_check=dict(environment='figma-desktop',loaded_styles=['Regular','Medium','Bold'],
                             missing_fonts=False,evidence='synthetic font-load fixture'),
             header=dict(brand_node_id='brand',category_node_id='category'),
             logo=dict(node_id='logo',effective_visible=True,bounds=dict(x=48,y=1220,width=200,height=60)),
             content_bounds=dict(x=48,y=240,width=984,height=800),
             visual_review=dict(evidence='synthetic screenshot fixture',contrast=True,faces_clear=True,
                                asset_matches_copy=True,logo_clear=True))
    def node(id,text,y,size,style):
        return dict(node_id=id,text=text,effective_visible=True,missing_font=False,clipped=False,
                    bounds=dict(x=48,y=y,width=984,height=size*1.5),auto_resize='HEIGHT',paragraph_spacing=0,
                    font_runs=[dict(family='Neulis Alt',style=style,font_size=size,line_height_px=size*1.5)])
    c = job['pages'][0]['content']
    r['text_nodes']=[node('t1',c['title'],240,48,'Bold'),node('t2',c['body'],352,48,'Medium'),
                     node('t3',c['support'],464,40,'Medium'),node('brand','Transit',40,28,'Regular'),
                     node('category','Event',100,28,'Regular')]
    r['text_node_count']=len(r['text_nodes'])
    return job


class RenderRegressionTests(unittest.TestCase):
    def setUp(self):
        self.job=strict_job()
        self.r=self.job['pages'][0]['render']
        self.n=self.r['text_nodes'][0]

    def fails(self, fragment):
        errors=MODULE.validate(self.job)
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_full_contract_passes(self):
        self.assertEqual(MODULE.validate(self.job),[])

    def test_release_requires_current_contract_and_reviews(self):
        self.job['state']='user_approved'
        self.assertFalse(MODULE.readiness(self.job)['ready'])
        self.job['qa'].update(typography=True,element_layout=True)
        self.assertTrue(MODULE.readiness(self.job)['ready'])
        self.assertFalse(MODULE.readiness(self.job)['external_publish_authorized'])

    def test_resize_reset_cannot_pass_as_single_line(self):
        self.n['auto_resize']='NONE'
        self.fails('auto-height-zero-paragraph-spacing-required')

    def test_automatic_wrap_exceeds_limit(self):
        self.n['bounds']['height']=216
        self.fails('measured-line-count-mismatch')

    def test_height_and_report_must_agree(self):
        self.n['bounds']['height']=144
        self.fails('measured-line-count-mismatch')

    def test_partial_line_or_negative_geometry_fails(self):
        self.n['bounds']['height']=80
        self.fails('measured-line-count-mismatch')
        self.n['bounds']['height']=-1
        self.fails('clipped-or-outside-canvas')

    def test_explicit_blank_lines_count(self):
        self.job['pages'][0]['content']['title']='기록\n\n나누기'
        self.n['text']='기록\n\n나누기'
        self.fails('lines-3>2')

    def test_hidden_ancestor_and_missing_font_are_blocked(self):
        for key,value in [('effective_visible',False),('missing_font',True),('clipped',True)]:
            with self.subTest(key=key):
                j=strict_job();j['pages'][0]['render']['text_nodes'][0][key]=value
                self.assertTrue(MODULE.validate(j))

    def test_header_font_is_in_full_inventory(self):
        self.r['text_nodes'][-1]['font_runs'][0]['family']='Pretendard'
        self.fails('neulis-alt-required')

    def test_shrinking_font_or_changing_leading_fails(self):
        self.n['font_runs'][0]['font_size']=40
        self.fails('measured-role-typography-mismatch')
        self.n['font_runs'][0]['font_size']=48
        self.n['font_runs'][0]['line_height_px']=48
        self.fails('measured-role-typography-mismatch')

    def test_font_load_evidence_required(self):
        self.r['font_check']['loaded_styles']=['Regular']
        self.fails('loaded-neulis-evidence-required')

    def test_changed_copy_requires_new_measurement(self):
        self.n['text']='다른 내용'
        self.fails('rendered-copy-mismatch')

    def test_collapsed_photo_frame_fails(self):
        self.r['canvas'].update(width=984,height=80)
        self.fails('canvas:expected-1080x1350')

    def test_removed_category_header_fails(self):
        self.r['text_nodes'][-1]['text']=''
        self.fails('header:missing-or-wrong-label')

    def test_shared_header_node_fails(self):
        self.r['header']['category_node_id']='brand'
        self.fails('distinct-brand-and-category-required')

    def test_missing_logo_fails(self):
        self.r['logo']={}
        self.fails('logo:missing-or-outside-canvas')

    def test_logo_and_text_collision_fails(self):
        self.r['logo']['bounds']['y']=240
        self.fails('layout:text-overlaps-logo')

    def test_slot_collision_and_reversed_order_fail(self):
        self.r['text_nodes'][1]['bounds']['y']=240
        self.fails('content-slots-overlap')
        self.r['text_nodes'][1]['bounds']['y']=190
        self.fails('title-body-support-order')

    def test_content_budget_measured(self):
        self.r['content_bounds']['height']=900
        self.fails('measured-content-height-or-bounds')

    def test_inventory_count_and_duplicate_ids(self):
        self.r['text_node_count']=4
        self.fails('count-mismatch')
        self.r['text_nodes'][-1]['node_id']='brand'
        self.fails('duplicate-node')

    def test_malformed_slot_node_does_not_crash(self):
        self.r['slots']['title']['node_id']={}
        self.fails('missing-measured-node')

    def test_visual_issues_require_manual_review(self):
        for key in ['contrast','faces_clear','asset_matches_copy','logo_clear']:
            with self.subTest(key=key):
                j=strict_job();j['pages'][0]['render']['visual_review'][key]=False
                self.assertTrue(any('visual:review-evidence-required' in e for e in MODULE.validate(j)))

    def test_editable_poster_requires_fixed_geometry(self):
        page={'pattern':'poster-cover','poster_content':{'title':'예시'}}
        self.r.update(poster_bounds=dict(x=190,y=210,width=700,height=937),poster_size_mode='FIXED')
        self.assertEqual(MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'),[])
        self.r['poster_size_mode']='HUG'
        self.assertIn('poster:fixed-700x937-required',MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'))
        self.r['poster_size_mode']='FIXED';self.r['poster_bounds']['height']=528
        self.assertIn('poster:fixed-700x937-required',MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'))

    def test_poster_copy_budget_is_checked(self):
        page={'id':'poster','pattern':'poster-cover','asset_ref':'editable-fixture','content':{},
              'poster_content':{'eyebrow':'예시','title':'가'*25,'body':'본문','support':'보조'}}
        self.job['state']='draft';self.job['pages']=[page]
        self.fails('artwork.title:chars-25>24')

    def test_track_artwork_and_row_geometry(self):
        page={'pattern':'track-list'}
        self.r['content_bounds']=dict(x=48,y=204,width=984,height=942)
        self.r['elements']=[dict(kind='track-row',container_node_id='row',effective_visible=True,
            bounds=dict(x=256,y=400,width=568,height=746),artwork_node_id='art',artwork_visible=True,
            artwork_bounds=dict(x=280,y=424,width=520,height=520))]
        self.assertEqual(MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'),[])
        self.r['elements'][0]['artwork_visible']=False
        self.assertIn('element:visible-artwork-required',MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'))
        self.r['elements'][0]['bounds']['height']=100
        self.assertIn('element:measured-row-bounds',MODULE.validate_render_evidence(page,self.r,{},MODULE.catalog(),'event'))

    def test_decision_log_contract(self):
        import json
        path=MODULE.ROOT/'decision-log.jsonl'
        for line in path.read_text().splitlines():
            self.assertEqual(MODULE.validate_decision(json.loads(line)),[])

    def test_structured_row_must_be_visible_and_contain_its_text(self):
        page={'pattern':'track-list'}
        rule=MODULE.catalog()['patterns']['editorial']['slots']['title']
        texts={'items.0.title':(self.n['text'],rule)}
        self.r['slots']['items.0.title']=self.r['slots']['title']
        self.r['elements']=[dict(kind='track-row',container_node_id='row',effective_visible=False,
            bounds=dict(x=48,y=450,width=984,height=192),artwork_node_id='art',artwork_visible=True)]
        errors=MODULE.validate_render_evidence(page,self.r,texts,MODULE.catalog(),'event')
        self.assertIn('element:hidden-container',errors)
        self.assertIn('element:text-outside-own-row',errors)

    def test_structured_rows_follow_title_and_do_not_overlap(self):
        page={'pattern':'track-list'}
        rule=MODULE.catalog()['patterns']['editorial']['slots']['title']
        texts={'title':(self.n['text'],rule)}
        self.r['elements']=[dict(kind='track-row',container_node_id=f'row{i}',effective_visible=True,
            bounds=dict(x=48,y=240,width=984,height=192),artwork_node_id=f'art{i}',artwork_visible=True) for i in range(2)]
        errors=MODULE.validate_render_evidence(page,self.r,texts,MODULE.catalog(),'event')
        self.assertIn('element:title-rows-support-order',errors)
        self.assertIn('element:row-order-or-overlap',errors)
