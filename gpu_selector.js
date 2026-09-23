/* The GPU model picker is the only React-owned part of the existing page. */
(function () {
  const h = React.createElement;
  const roots = new WeakMap();

  function GPUModelButton({ model, selected, index, onSelect }) {
    return h('button', {
      type:'button',
      className:`gpu-model-chip${selected ? ' selected' : ''}`,
      'aria-label':model,
      'aria-pressed':selected,
      onClick:() => onSelect(model),
      style:{ '--chip-index':index },
    }, model.replace(/^(RTX|GTX|RX)\s+/, ''));
  }

  function GPUSeriesPill({ group, expanded, selectedModel, onToggle, onSelectModel }) {
    const id = `gpu-models-${group.label.replace(/\W+/g, '-').toLowerCase()}`;
    return h('div', { className:`gpu-series-pill${expanded ? ' expanded' : ''}` },
      h('button', {
        type:'button', className:'gpu-series-trigger',
        'aria-expanded':expanded, 'aria-controls':id,
        onClick:() => onToggle(group.label),
      }, group.label, group.models.includes(selectedModel) ? h('span', { className:'gpu-series-dot', 'aria-hidden':true }) : null),
      h('div', { className:'gpu-model-track', id, 'aria-hidden':!expanded },
        group.models.map((model, index) => h(GPUModelButton, {
          key:model, model, index, selected:model === selectedModel,
          onSelect:onSelectModel,
        })),
      ),
    );
  }

  function GPUBrandSection({ brand, groups, openSeries, selectedModel, onToggle, onSelectModel }) {
    return h('section', { className:'gpu-brand-section', 'aria-label':brand },
      h('div', { className:'gpu-vendor-label' }, brand),
      h('div', { className:'gpu-series-list' }, groups.map(group => h(GPUSeriesPill, {
        key:group.label, group, expanded:openSeries === group.label,
        selectedModel, onToggle, onSelectModel,
      }))),
    );
  }

  function GPUSelector({ groups, selectedModel, onSelectModel }) {
    const [openSeries, setOpenSeries] = React.useState('');
    const visibleOpenSeries = groups.some(group => group.label === openSeries) ? openSeries : '';
    const onToggle = label => setOpenSeries(current => current === label ? '' : label);
    const brands = ['NVIDIA', 'AMD'];
    return groups.length
      ? h('div', { className:'gpu-selector' }, brands.map(brand => {
          const brandGroups = groups.filter(group => group.vendor === brand);
          return brandGroups.length ? h(GPUBrandSection, {
            key:brand, brand, groups:brandGroups, openSeries:visibleOpenSeries,
            selectedModel, onToggle, onSelectModel,
          }) : null;
        }))
      : h('span', { className:'product-source' }, '선택 가능한 옵션 없음');
  }

  window.GpuModelSelector = {
    render(host, props) {
      let root = roots.get(host);
      if (!root) {
        root = ReactDOM.createRoot(host);
        roots.set(host, root);
      }
      root.render(h(GPUSelector, props));
    },
    unmount(host) {
      const root = roots.get(host);
      if (root) root.unmount();
      roots.delete(host);
    },
  };
})();
