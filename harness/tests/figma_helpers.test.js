const test = require('node:test');
const assert = require('node:assert/strict');
const {loadNeulis,setText,replaceContent,fixPosterSize,captureFrame} = require('../scripts/figma_helpers');
const styles=['Regular','Medium','Bold'];
const font=(style='Medium')=>({family:'Neulis Alt',style});
const api=()=>({listAvailableFontsAsync:async()=>styles.map(s=>({fontName:font(s)})),loadFontAsync:async()=>{}});
const text=()=>({id:'text',type:'TEXT',height:72,textAutoResize:'HEIGHT',
  parent:{layoutMode:'VERTICAL'},getStyledTextSegments:()=>[{fontName:font()}],
  resize(w,h){this.width=w;this.height=h;this.textAutoResize='NONE';}});

test('resize resetting text to NONE is repaired after resize',async()=>{
 const n=text();await setText(api(),n,'본문',{font_style:'Medium',font_size:48,line_height_percent:150},984);
 assert.equal(n.textAutoResize,'HEIGHT');assert.equal(n.layoutSizingVertical,'HUG');
 assert.equal(n.characters,'본문');assert.equal(n.visible,true);assert.equal(n.paragraphSpacing,0);
});
test('missing Neulis stops before font loading and never substitutes',async()=>{
 let loads=0;const f=api();f.listAvailableFontsAsync=async()=>[];f.loadFontAsync=async()=>loads++;
 await assert.rejects(loadNeulis(f),/Neulis Alt unavailable/);assert.equal(loads,0);
});
test('all three styles must be loadable',async()=>{
 const f=api();let loaded=[];f.loadFontAsync=async n=>loaded.push(n);
 const r=await loadNeulis(f);assert.deepEqual(loaded,styles.map(font));assert.deepEqual(r.loaded_styles,styles);
});
test('unexpected source font is blocked',async()=>{
 const n=text();n.getStyledTextSegments=()=>[{fontName:{family:'Pretendard',style:'Regular'}}];
 await assert.rejects(loadNeulis(api(),[n]),/Unexpected source font/);
});
test('failed target font load leaves text untouched',async()=>{
 const n=text();n.characters='원본';const f=api();f.loadFontAsync=async()=>{throw Error('unavailable');};
 await assert.rejects(setText(f,n,'변경',{font_style:'Bold',font_size:48},984));assert.equal(n.characters,'원본');
});
test('source, root frame and direct TEXT are protected from container replacement',()=>{
 const root={id:'copy'},source={id:'source'};
 assert.throws(()=>replaceContent(root,root,{},{}),/Original source/);
 assert.throws(()=>replaceContent(source,root,root,{}),/dedicated content/);
 assert.throws(()=>replaceContent(source,root,{type:'TEXT',parent:root},{}),/direct TEXT/);
});
test('container containing header or logo cannot be removed',()=>{
 const root={id:'copy'},old={id:'content',type:'FRAME',parent:root,findAll:()=>[{id:'header'}]};
 assert.throws(()=>replaceContent({id:'source'},root,old,{},['header']),/protected header/);
});
test('poster retains 700 by 937 fixed size',()=>{
 const p={layoutSizingVertical:'HUG',resize(w,h){this.width=w;this.height=h;}};
 fixPosterSize(p);assert.equal(p.width,700);assert.equal(p.height,937);assert.equal(p.layoutSizingVertical,'FIXED');
});
function frameFixture(){
 const frame={id:'frame',type:'FRAME',width:1080,height:1350,absoluteBoundingBox:{x:20,y:20,width:1080,height:1350}};
 const group={id:'group',type:'FRAME',parent:frame,visible:false};
 const n={id:'t',type:'TEXT',characters:'예시',parent:group,textAutoResize:'HEIGHT',paragraphSpacing:0,hasMissingFont:false,
   absoluteBoundingBox:{x:68,y:260,width:984,height:72},getStyledTextSegments:()=>[{fontName:font(),fontSize:48,lineHeight:{unit:'PERCENT',value:150}}]};
 const logo={id:'logo',type:'VECTOR',parent:frame,absoluteBoundingBox:{x:68,y:1240,width:100,height:60}};
 frame.findAll=()=>[group,n,logo];return{frame,n,group};
}
test('capture includes ancestor visibility and refuses to fabricate visual review',()=>{
 const {frame}=frameFixture();const r=captureFrame(frame,{slots:{body:'t'},logo:'logo'},{});
 assert.equal(r.text_nodes[0].effective_visible,false);assert.equal(r.slots.body.lines,1);
 assert.equal(r.visual_review,undefined);assert.equal(r.text_nodes[0].bounds.y,240);
});
test('fixed height cannot be reported as measured line count',()=>{
 const {frame,n}=frameFixture();n.textAutoResize='NONE';
 assert.equal(captureFrame(frame,{slots:{body:'t'},logo:'logo'},{}).slots.body.lines,null);
});
test('mixed line height cannot be reported as measured line count',()=>{
 const {frame,n}=frameFixture();n.getStyledTextSegments=()=>[48,40].map(s=>({fontName:font(),fontSize:s,lineHeight:{unit:'PERCENT',value:150}}));
 assert.equal(captureFrame(frame,{slots:{body:'t'},logo:'logo'},{}).slots.body.lines,null);
});
