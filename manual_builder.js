/* React owns the manual builder. Domain state and provider requests remain in
   app_utils.js; this adapter replaces only rendering, never the price pipeline. */
(function () {
  const h = React.createElement;
  const {useState, useRef, useLayoutEffect} = React;
  const host = document.getElementById('manualBuilderRoot');
  if (!host) return;
  const performancePanel = document.getElementById('legacyPerformance');
  const root = ReactDOM.createRoot(host);
  const headerHost = document.querySelector('.hero');
  headerHost.replaceChildren();
  let queued = false;
  const icons = {cpu:'M8 8h8v8H8z M5 9H2m3 6H2m20-6h-3m3 6h-3M9 5V2m6 3V2M9 22v-3m6 3v-3 M5 5h14v14H5z',mb:'M5 3h14v18H5z M8 6h5v5H8z M8 15h8m-8 3h8m0-12v5',gpu:'M3 6h18v12H3z M7 18v3m4-3v3 M8 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M17 9v6',ram:'M2 7h20v10H2z M5 10h3v4H5zm6 0h3v4h-3zm6 0h2v4h-2 M5 17v3m4-3v3m4-3v3m4-3v3',storage:'M6 4h12l3 16H3z M4 16h16',hdd:'M5 3h14v18H5z M12 7a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 11l4 4',psu:'M13 2L4 14h7l-1 8 10-13h-7z',case:'M6 2h12v20H6z M9 6h6m-6 4h6m-6 7h1',software:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',search:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6',close:'M6 6l12 12M18 6L6 18',down:'M5 9l7 7 7-7',check:'M5 12l4 4L19 6',reset:'M3 10a9 9 0 1 1 1 8 M3 3v7h7'};
  function Icon({name, size=20}) { return h('svg',{width:size,height:size,viewBox:'0 0 24 24',fill:'none',stroke:'currentColor',strokeWidth:1.7,strokeLinecap:'round',strokeLinejoin:'round','aria-hidden':true},h('path',{d:icons[name] || icons.cpu})); }
  function Button({children,onClick,className='',...props}) {return h('button',{type:'button',className:'pc-button '+className,onClick,...props},children);}
  function Header() {return ReactDOM.createPortal(h(React.Fragment,null,
    h('div',{className:'pc-brand'},h(Icon,{name:'cpu',size:26}),h('div',null,h('h1',null,'PC 견적 도우미'),h('p',null,'부품 선택부터 예상 성능까지, 한곳에서'))),
    h('nav',{className:'pc-mode-switch','aria-label':'견적 방식 선택'},[['ai','AI 자동 추천'],['custom','직접 사양 선택']].map(([view,label])=>h(Button,{key:view,id:view==='custom'?'viewCustomBtn':'viewAiBtn','aria-pressed':st.activeView===view,className:st.activeView===view?'is-active':'',onClick:()=>{setActiveView(view);refresh(); if(view==='custom')void refreshProductBrowserPrices();}},label)))),headerHost);}
  function Categories({type,parts}) {return h('nav',{className:'pc-categories','aria-label':'부품 카테고리'},BUILDER_PARTS.map(meta=>h(Button,{key:meta.key,'aria-pressed':type===meta.key,className:type===meta.key?'is-active':'',onClick:()=>setBuilderPart(meta.key)},h(Icon,{name:meta.key}),h('span',null,meta.label),parts[meta.key]?h('span',{className:'pc-category-check'},h(Icon,{name:'check',size:14})):null)));}
  function toggle(type,key,value) {toggleBuilderFilter(type,key,value);}
  function FilterGroup({group,type}) {
    const [expanded,setExpanded]=useState(false);
    const limit=group.key==='socket'?4:6;
    const selected=filterValues(type,group.key);
    const visible=expanded?group.options:group.options.filter((option,index)=>index<limit || selected.includes(option[0]));
    return h('div',{className:'pc-filter-row',role:'group','aria-label':group.label},h('div',{className:'pc-filter-label'},group.label),h('div',{className:'pc-filter-options'},visible.map(([value,label])=>h(Button,{key:value,'aria-pressed':selected.includes(String(value)),className:'pc-chip'+(selected.includes(String(value))?' is-active':''),onClick:()=>toggle(type,group.key,String(value))},type==='cpu'&&group.key==='platform'?String(label).replace(' CPU용',''):label)),group.options.length>limit?h(Button,{className:'pc-options-more','aria-expanded':expanded,onClick:()=>setExpanded(!expanded)},expanded?'접기':'옵션 더보기',h(Icon,{name:'down',size:14})):null));
  }
  function GpuHierarchy() {
    const groups=gpuSeriesGroups(allKnownProductsFor('gpu')).filter(g=>!filterValues('gpu','vendor').length||filterValues('gpu','vendor').includes(g.vendor.toLowerCase()));
    const series=filterValues('gpu','series')[0];
    const modern=groups.filter(g=>/RTX (50|40|30)|RX (9000|7000|6000)/.test(g.label));
    const older=groups.filter(g=>!modern.includes(g));
    const [legacy,setLegacy]=useState(false);
    const active=groups.find(g=>g.label.replace(/ Series$/,'')===series);
    return h('div',{className:'pc-gpu-hierarchy'},h('div',{className:'pc-filter-row'},h('div',{className:'pc-filter-label'},'GPU 시리즈'),h('div',{className:'pc-filter-options'},(legacy?groups:modern).map(g=>h(Button,{key:g.label,className:'pc-chip'+(g===active?' is-active':''),'aria-pressed':g===active,onClick:()=>selectGpuSeries(g.label)},g.label.replace(' Series',''))),older.length?h(Button,{className:'pc-options-more',onClick:()=>setLegacy(!legacy),'aria-expanded':legacy},legacy?'접기':'옵션 더보기'):null)),active?h('div',{className:'pc-filter-row'},h('div',{className:'pc-filter-label'},'세부 칩셋'),h('div',{className:'pc-filter-options'},h(Button,{className:'pc-chip'+(!filterValues('gpu','model').length?' is-active':''),'aria-pressed':!filterValues('gpu','model').length,onClick:()=>selectGpuSeries(active.label)},'시리즈 전체'),active.models.map(model=>h(Button,{key:model,className:'pc-chip'+(filterValues('gpu','model').includes(model)?' is-active':''),'aria-pressed':filterValues('gpu','model').includes(model),onClick:()=>{st.builderFilters.gpu={...st.builderFilters.gpu,model:[model]};refresh();void refreshProductBrowserPrices();}},model)))):null);
  }
  function Filters({type}) {
    const [open,setOpen]=useState(true);
    const [extra,setExtra]=useState(false);
    const defs=type!=='gpu'&&!st.productFacets?.[type]?[]:builderFilterDefs(type);
    const primary={mb:['manufacturer','socket','chipset','memory_type','form_factor'],ram:['manufacturer','memory_type','capacity_gb','speed','cl'],hdd:['manufacturer','usage','form_factor','capacity_gb','rpm']}[type] || defs.slice(0,5).map(g=>g.key);
    const shown=extra?defs:defs.filter(g=>primary.includes(g.key) || filterValues(type,g.key).length);
    const active=Object.entries(st.builderFilters[type]||{}).flatMap(([key,values])=>values.map(value=>({key,value,label:defs.find(d=>d.key===key)?.options.find(o=>o[0]===value)?.[1]||value})));
    return h('div',{className:'pc-filters'},h('div',{className:'pc-filter-heading'},h(Button,{className:'pc-filter-toggle','aria-expanded':open,onClick:()=>setOpen(!open)},'상세 조건',h(Icon,{name:'down',size:16})),h('span',null,'항목 간 조건을 함께 적용해요'),h(Button,{className:'pc-text-button',id:'resetProductFiltersBtn',onClick:resetFilters},h(Icon,{name:'reset',size:14}),'초기화')),
      open?h('div',{className:'pc-filter-body',id:'builderFilters'},shown.map(group=>type==='gpu'&&group.key==='model'?h(GpuHierarchy,{key:'gpu'}):h(FilterGroup,{key:type+group.key,group,type})),defs.length>primary.length?h(Button,{className:'pc-extra-filters','aria-expanded':extra,onClick:()=>setExtra(!extra)},extra?'주요 조건만 보기':`상세 항목 ${defs.length-primary.length}개 더보기`,h(Icon,{name:'down',size:14})):null):null,
      active.length?h('div',{className:'pc-active-filters',id:'activeProductFilters'},h('span',null,'선택 조건 '+active.length),active.map(a=>h(Button,{key:a.key+a.value,className:'pc-active-chip','aria-label':a.label+' 조건 해제',onClick:()=>toggle(type,a.key,a.value)},a.label,h(Icon,{name:'close',size:13})))):null);
  }
  function resetFilters() {st.builderFilters[st.builderPart]={};if(st.builderPart==='gpu')st.csGpuMakers=[];refresh();void refreshProductBrowserPrices();}
  function Search({type}) {
    const [draft,setDraft]=useState(st.productQuery||'');
    const search=e=>{e?.preventDefault();st.productQuery=draft.trim();clearTimeout(productSearchTimer);void refreshProductBrowserPrices({query:st.productQuery});refresh();};
    return h('div',{className:'pc-browser-head'},h('div',null,h('h3',{id:'builderCategoryTitle'},BUILDER_META[type].label),h('p',null,'필요한 사양으로 좁혀보세요')),
      h('form',{className:'pc-search',role:'search',onSubmit:search},h(Icon,{name:'search',size:19}),h('input',{id:'productSearchInput',type:'search',value:draft,onChange:e=>setDraft(e.target.value),placeholder:'제품명, 칩셋, 소켓 검색','aria-label':'부품 검색'}),h('button',{type:'submit',id:'refreshProductsBtn',className:'pc-button pc-primary'},'검색')));
  }
  function ProductImage({part,type}) {return h('span',{className:'pc-product-image'},h('img',{src:partImageUrl(part,type),alt:fullProductName(part)+' 제품 이미지',loading:'lazy',decoding:'async',onError:e=>{if(!e.currentTarget.dataset.failed){e.currentTarget.dataset.failed='1';e.currentTarget.src=imageFallbackUrl(part);}}}));}
  function badges(part,type) {
    if(!part.specs)return productBadges(part,type);
    const s=part.specs; const keys={cpu:['socket','cpu_family','memory_type'],mb:['chipset','socket','memory_type','form_factor'],ram:['memory_type','kit','capacity_gb','speed','cl'],gpu:['chipset','vram_gb'],storage:['form_factor','interface','capacity_gb','nand'],psu:['watt','rating','modular','atx_version'],hdd:['usage','capacity_gb','rpm']}[type]||[];
    return keys.flatMap(key=>{const value=s[key];if(!value)return[];if(Array.isArray(value))return value;return [key==='capacity_gb'||key==='vram_gb'?Number(value)>=1000?`${Number(value)/1000}TB`:`${value}GB`:key==='speed'?`${value}MT/s`:key==='cl'?`CL${value}`:key==='watt'?`${value}W`:key==='rpm'?`${value} RPM`:value];}).slice(0,6);
  }
  function ProductRow({part,type,selected}) {
    const price=effectivePrice(part);const provenance=priceProvenance(part);
    return h('article',{className:'pc-product-row'+(selected?' is-selected':''),'data-part-id':part.id},h(ProductImage,{part,type}),h('div',{className:'pc-product-info'},h('a',{className:'pc-product-name',href:partUrl(part),target:'_blank',rel:'noopener noreferrer'},fullProductName(part)),h('div',{className:'pc-specs'},badges(part,type).map((b,i)=>h('span',{key:i},b))),h('p',{className:'pc-price-source'},provenance.text)),h('div',{className:'pc-product-action'},h('strong',null,price==null?'가격 미확인':money(price)),h(Button,{className:selected?'pc-added':'pc-add','aria-pressed':selected,onClick:()=>selected?clearBuilderProduct(type):selectBuilderProduct(type,part.id)},h(Icon,{name:selected?'check':'close',size:14}),selected?'선택됨':'담기')));
  }
  function Results({type,parts}) {
    const browse=browseStateFor(type);const current=browse.requestKey===builderSearchKey(type)&&browse.loaded;
    const products=filteredProducts(type);
    return h(React.Fragment,null,h('div',{className:'pc-results-toolbar'},h('strong',{id:'productCount'},`${products.length}개 표시`),h('div',{className:'pc-results-controls'},h('select',{id:'productSourceSelect',value:st.productSource,'aria-label':'가격 검색처',onChange:e=>{st.productSource=e.target.value;void refreshProductBrowserPrices();refresh();}},['all','danawa','compuzone'].map((v,i)=>h('option',{key:v,value:v},['다나와 + 컴퓨존','다나와','컴퓨존'][i]))),h('select',{id:'productSortSelect',value:st.productSort,'aria-label':'제품 정렬',onChange:e=>{st.productSort=e.target.value;void refreshProductBrowserPrices();refresh();}},[['popular','검색처 기본순'],['price_asc','낮은 가격순'],['price_desc','높은 가격순'],['name','상품명순']].map(([value,label])=>h('option',{key:value,value},label))))),
      h('p',{className:'pc-result-note',role:'status',id:'productBrowseNote'},browse.loading?'조건에 맞는 제품과 가격을 검색하고 있어요.':browse.error?browse.error+' 이전 확인가·참고가를 표시합니다.':browse.partial?'일부 결과를 먼저 표시합니다. 더 보기로 검색을 이어갈 수 있어요.':'판매처 사양 기준 · 가격과 이름 정렬은 불러온 제품에 적용됩니다.'),
      h('div',{id:'productList',className:'pc-product-list','aria-busy':browse.loading},products.map(part=>h(ProductRow,{key:part.id,part,type,selected:parts[type]?.id===part.id})),!products.length?h('div',{className:'pc-empty'},h(Icon,{name:'search',size:32}),h('h4',null,browse.loading?'제품을 찾고 있어요':'조건에 맞는 제품이 없어요'),h('p',null,'검색어를 바꾸거나 선택 조건을 줄여보세요. 사양이 없는 제품은 조건 검색에서 제외됩니다.'),!browse.loading?h(Button,{onClick:resetFilters},'선택 조건 초기화'):null):null),
      current&&browse.hasMore?h(Button,{id:'loadMoreProductsBtn',className:'pc-load-more',disabled:browse.loading,onClick:()=>void refreshProductBrowserPrices({append:true})},browse.loading?'불러오는 중…':'제품 더 보기',h(Icon,{name:'down',size:16})):null);
  }
  function Compatibility({parts,inline=false}) {
    const status=socketCompatibility(parts.cpu,parts.mb);
    if(['incomplete','compatible'].includes(status.status))return null;
    const mismatch=status.status==='incompatible';
    return h('div',{className:'pc-compatibility '+(mismatch?'is-warning':'is-unknown'),role:'status','aria-live':'polite',id:inline?'manualCompatibilityInline':'manualCompatibility'},h('strong',null,mismatch?'CPU와 메인보드의 소켓이 호환되지 않습니다':'소켓 정보 확인이 필요합니다'),h('p',null,`CPU: ${fullProductName(parts.cpu)} · ${status.cpuSocket==='unknown'?'소켓 미확인':status.cpuSocket}`),h('p',null,`메인보드: ${fullProductName(parts.mb)} · ${status.motherboardSocket==='unknown'?'소켓 미확인':status.motherboardSocket}`));
  }
  function cartDisplayName(part,type) {
    const full=fullProductName(part);
    const specs=part.specs || {};
    if (type==='cpu') {
      const model=full.match(/(?:i[3579][- ]?\d{4,5}[a-z]*|\b\d{4}(?:X3D2?|XT|X|G|F)\b|\b\d{3}[KFT]+(?:\s+Plus)?)/i)?.[0];
      if(model) return [specs.cpu_family || (/라이젠|Ryzen/i.test(full)?'Ryzen':/울트라|Ultra/i.test(full)?'Core Ultra':'Intel Core'),model].join(' ').replace(/(Core i[3579]) i[3579][- ]/i,'$1-');
    }
    let short=full.replace(/^\[([^\]]+)\]\s*/,'$1 ').replace(/\([^)]*\)/g,'').replace(/\[[^\]]*\]/g,'');
    short=short.replace(/(?:대원씨티에스|인텍앤컴퍼니|제이씨현|피씨디렉트|코잇|에즈윈|디앤디컴|STCOM|대양케이스|서린|정품|멀티팩|벌크|병행수입|병행|해외구매|트라이프로져\d*|듀러블에디션)/gi,'');
    short=short.replace(/지포스|GeForce|라데온|Radeon/gi,'').replace(/\bD[567](?:X)?\b/gi,'');
    return short.replace(/\s+/g,' ').trim() || full;
  }
  function Cart({parts}) {
    const selected=Object.values(parts).filter(Boolean);const total=selected.reduce((sum,p)=>sum+(effectivePrice(p)||0),0);const unknown=selected.some(p=>effectivePrice(p)==null);
    return h('section',{className:'pc-cart'},h('div',{className:'pc-cart-head'},h('h3',null,'내 견적'),h('span',null,selected.length+' / '+BUILDER_PARTS.length),h(Button,{className:'pc-text-button',onClick:()=>{BUILDER_PARTS.forEach(meta=>{document.getElementById(meta.select).value='';});updateCustomChart();refresh();}},'전체 비우기')),
      h(Compatibility,{parts}),h('div',{className:'pc-cart-rows',id:'buildCart'},BUILDER_PARTS.map(meta=>{const part=parts[meta.key];return h('div',{key:meta.key,className:'pc-cart-item'+(part?' has-selection':'')+(st.builderPart===meta.key?' is-current':'')},h(Button,{className:'pc-cart-select',onClick:()=>setBuilderPart(meta.key)},part?h(ProductImage,{part,type:meta.key}):h(Icon,{name:meta.key,size:19}),h('span',{className:'pc-cart-name'},h('b',null,meta.label),part?h('span',{title:fullProductName(part)},cartDisplayName(part,meta.key)):null),!part?h('span',{className:'pc-cart-prompt'},'제품 선택'):null),part?h('div',{className:'pc-cart-item-bottom'},h('a',{href:partUrl(part),target:'_blank',rel:'noopener noreferrer'},effectivePrice(part)==null?'가격 미확인':money(effectivePrice(part))),h(Button,{className:'pc-icon-button','aria-label':meta.label+' 선택 해제',onClick:()=>clearBuilderProduct(meta.key)},h(Icon,{name:'close',size:14}))):null);})),
      h('div',{className:'pc-cart-total'},h('span',null,'부품 합계'),h('strong',null,money(total)+(unknown?' + 미확인':''))),h('p',{className:'pc-cart-note'},document.getElementById('csPriceNote')?.textContent||'배송비 및 조립비 별도'),h('p',{className:'pc-cart-note'},document.getElementById('csBuildValue')?.textContent||''));
  }
  function Performance() {
    const ref=useRef(null);
    useLayoutEffect(()=>{ref.current.appendChild(performancePanel);performancePanel.hidden=false;},[]);
    return h('section',{className:'pc-performance'},h('h3',null,'예상 성능'),h('div',{ref}));
  }
  function App() {
    const type=st.builderPart;
    const parts=selectedCustomParts();
    const selected=Object.values(parts).filter(Boolean);
    const total=selected.reduce((sum,p)=>sum+(effectivePrice(p)||0),0);
    return h(React.Fragment,null,
      h(Header),
      h('div',{className:'pc-workspace'},
        h(Categories,{type,parts}),
        h('main',{className:'pc-main'},
          h('div',{className:'pc-page-title'},
            h('h2',null,'나만의 PC, 직접 골라보세요'),
            h('p',null,'원하는 부품을 선택하고, 가격과 예상 성능을 함께 확인하세요.')),
          h('div',{className:'pc-mobile-warning'},h(Compatibility,{parts,inline:true})),
          h('section',{className:'pc-browser'},h(Search,{key:"search-"+type,type}),h(Filters,{key:"filters-"+type,type}),h(Results,{type,parts}))),
        h('aside',{className:'pc-estimate',tabIndex:0,'aria-label':'내 견적과 예상 성능 · 독립 스크롤'},h(Cart,{parts}),h(Performance)),
        h(Button,{className:'pc-mobile-cart-bar',onClick:()=>document.querySelector('.pc-cart').scrollIntoView({behavior:'smooth',block:'start'})},
          `내 견적 · ${selected.length}개 선택`,h('strong',null,money(total)))));
  }
  function refresh() {if(queued)return;queued=true;queueMicrotask(()=>{queued=false;root.render(h(App));});}
  window.ManualBuilder={refresh};
  refresh();
  setActiveView('custom');
  void refreshProductBrowserPrices();
})();
