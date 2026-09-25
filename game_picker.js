// Keep the native select as the form/event source.
(() => {
  const pickers = new WeakMap();
  const fallback = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="32"><rect width="48" height="32" rx="6" fill="#dbeafe"/><path d="M15 10h18l5 14h-7l-3-4h-8l-3 4h-7z" fill="#2563eb"/><path d="M17 13v6m-3-3h6" stroke="white" stroke-width="2"/><circle cx="30" cy="15" r="2" fill="white"/></svg>');
  function icon(id) {
    const image = document.createElement('img');
    image.alt = ''; image.width = 42; image.height = 28;
    image.src = '/assets/game-icons/' + encodeURIComponent(id) + '.jpg';
    image.addEventListener('error', () => { image.src = fallback; }, { once: true });
    return image;
  }
  function contents(element, option) {
    element.replaceChildren(icon(option.value), document.createTextNode(option.textContent));
  }
  window.refreshGamePicker = function(select) {
    let picker = pickers.get(select);
    if (!picker) {
      const wrapper = document.createElement('div'); wrapper.className = 'game-picker';
      const button = document.createElement('button'); button.type = 'button'; button.className = 'game-picker-trigger';
      button.setAttribute('aria-label', select.getAttribute('aria-label') || '게임 선택');
      button.setAttribute('aria-haspopup', 'listbox');
      const list = document.createElement('div'); list.className = 'game-picker-options';
      list.id = select.id + '-options'; list.setAttribute('role', 'listbox');
      list.setAttribute('aria-label', '게임 목록'); list.hidden = true;
      button.setAttribute('aria-controls', list.id); button.setAttribute('aria-expanded', 'false');
      select.before(wrapper); wrapper.append(button, list);
      select.hidden = true;
      const close = () => { list.hidden = true; button.setAttribute('aria-expanded','false'); };
      const open = () => {
        const bounds = button.getBoundingClientRect();
        const above = bounds.top, below = innerHeight - bounds.bottom;
        const upward = below < 280 && above > below;
        list.style.top = upward ? 'auto' : 'calc(100% + 5px)';
        list.style.bottom = upward ? 'calc(100% + 5px)' : 'auto';
        list.style.maxHeight = Math.max(100, Math.min(280, (upward ? above : below) - 12)) + 'px';
        list.hidden = false; button.setAttribute('aria-expanded','true');
        (list.querySelector('[aria-selected="true"]') || list.firstElementChild)?.focus();
      };
      button.addEventListener('click', () => list.hidden ? open() : close());
      button.addEventListener('keydown', e => {
        if (['ArrowDown','ArrowUp'].includes(e.key)) { e.preventDefault(); open(); }
      });
      list.addEventListener('keydown', e => {
        const options = [...list.children], index = options.indexOf(document.activeElement);
        if (e.key === 'Escape') { e.preventDefault(); close(); button.focus(); }
        else if (['ArrowDown','ArrowUp','Home','End'].includes(e.key)) {
          e.preventDefault();
          const next = e.key === 'Home' ? 0 : e.key === 'End' ? options.length-1 :
            (index + (e.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
          options[next]?.focus();
        } else if (e.key.length === 1 && e.key !== ' ') {
          const match = options.find((o,i) => i>index && o.textContent.toLowerCase().startsWith(e.key.toLowerCase())) ||
            options.find(o => o.textContent.toLowerCase().startsWith(e.key.toLowerCase()));
          match?.focus();
        }
      });
      wrapper.addEventListener('focusout', e => { if (!wrapper.contains(e.relatedTarget)) close(); });
      document.addEventListener('pointerdown', e => { if (!wrapper.contains(e.target)) close(); });
      picker = {button,list,close}; pickers.set(select,picker);
      select.addEventListener('change', () => window.refreshGamePicker(select));
    }
    const selected = select.selectedOptions[0];
    if (selected) contents(picker.button, selected);
    picker.list.replaceChildren();
    for (const option of select.options) {
      const item = document.createElement('button'); item.type = 'button'; item.tabIndex = -1;
      item.setAttribute('role','option'); item.setAttribute('aria-selected', String(option.selected));
      item.dataset.value = option.value; contents(item,option);
      item.addEventListener('click', () => {
        select.value = option.value; picker.close(); picker.button.focus();
        select.dispatchEvent(new Event('change', {bubbles:true}));
      });
      picker.list.append(item);
    }
  };
})();
