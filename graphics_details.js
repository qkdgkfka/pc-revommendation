(function () {
  'use strict';
  const h = React.createElement;
  const roots = new WeakMap();
  let serial = 0;
  const display = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('ko-KR', {maximumFractionDigits:1}) : '—';
  function GraphicsDetails({fps, id}) {
    const [open, setOpen] = React.useState(false);
    const rows = (fps.graphics_modes || []).filter(row => row.supported &&
      ['upscale', 'fg2', 'mfg4', 'upscale_fg_measured'].includes(row.id));
    return h('div', {className:'graphics-details'},
      h('button', {type:'button', className:'graphics-toggle', 'aria-expanded':open,
        'aria-controls':id, onClick:() => setOpen(value => !value)},
        open ? 'DLSS · 프레임 생성 접기 −' : 'DLSS · 프레임 생성 보기 +'),
      open ? h('div', {id, className:'graphics-panel'},
        rows.length ? rows.map(row => h('div', {className:'graphics-mode', key:row.id},
          h('div', {className:'graphics-mode-heading'},
            h('strong', null, row.label),
            h('span', {className:'graphics-method'}, row.method === 'mode_measurement' ? '실측' : '예상')),
          h('div', {className:'graphics-mode-value'},
            h('strong', null, display(row.avg_fps) + ' FPS'),
            row.generated && row.render_fps != null ? h('span', null, '실제 렌더링 ' + display(row.render_fps) + ' FPS') : null),
          row.method !== 'mode_measurement' && row.range ? h('p', null,
            '예상 범위 ' + display(row.range.min) + '–' + display(row.range.max) + ' FPS') : null,
          row.id === 'upscale_fg_measured' ? h('p', null, '원문 DLSS 품질·FG 배율은 공개되지 않았습니다.') : null,
          row.preset_label ? h('p', null, row.preset_label + ' · 기준 자료 ' + row.reference_resolution + 'p') : null,
          row.support_note ? h('p', null, row.support_note) : null,
          row.source_url && /^https:\/\//.test(row.source_url) ? h('a', {href:row.source_url, target:'_blank', rel:'noopener noreferrer'},
            row.method.startsWith('mode_') ? '측정 출처' : '기능 지원 정보') : null))
          : h('p', null, '이 게임·GPU에서 지원이 확인된 DLSS/FSR·프레임 생성 옵션이 없습니다.'),
        rows.some(row => row.generated) ? h('p', {className:'graphics-footnote'},
          'FG는 생성 프레임을 포함한 화면 표시 FPS입니다. 조작 반응 속도는 실제 렌더링 FPS와 다릅니다.') : null,
        rows.some(row => row.method !== 'mode_measurement') ? h('p', {className:'graphics-footnote'},
          '예상값은 구성과 렌더링 부하를 반영한 계산값이며 실측값이 아닙니다.') : null) : null);
  }
  window.GraphicsDetails = {
    mount(container, fps) {
      if (!container || !fps?.fps_by_option) return;
      const node = document.createElement('div');
      node.className = 'graphics-react-root';
      container.appendChild(node);
      const root = ReactDOM.createRoot(node);
      roots.set(node, root);
      root.render(h(GraphicsDetails, {fps, id:'graphics-modes-' + (++serial)}));
    },
    unmountWithin(container) {
      container?.querySelectorAll('.graphics-react-root').forEach(node => {
        roots.get(node)?.unmount(); roots.delete(node); node.remove();
      });
    }
  };
})();
