/* Shared image markup, hover previews, and fallbacks for both builder and recommendations. */
function partImageUrl(part, type = '') {
  if (!part?.name && !part?.product_name) return '';
  const name = part.product_name || part.name;
  const params = queryString({
    name:String(name), type:String(type || part.part_type || part.type || ''),
    image_url:/^https?:\/\//i.test(part.image_url || '') && !String(part.image_url).includes('/api/part-image') ? part.image_url : '',
    product_url:partUrl(part),
  });
  return `${baseUrl()}/api/part-image?${params}`;
}
function previewAttrs(part, type = '') {
  if (!part?.name && !part?.product_name) return '';
  const price = effectivePrice(part);
  const data = {
    'preview-url': partUrl(part),
    'preview-name': fullProductName(part),
    'preview-image': partImageUrl(part, type),
    'preview-fallback': imageFallbackUrl(part),
    'preview-price': price != null ? money(price) : '',
    'preview-source': priceProvenance(part).text,
  };
  return Object.entries(data)
    .map(([key, value]) => `data-${key}="${escapeHtml(value)}"`)
    .join(' ');
}
function partThumb(part, type = '', className = 'part-thumb') {
  const src = partImageUrl(part, type);
  if (!src) return `<span class="${className}"></span>`;
  return `<span class="${className} image-loading"><img src="${escapeHtml(src)}" data-image-fallback="${escapeHtml(imageFallbackUrl(part))}" alt="${escapeHtml(displayName(part))} 제품 이미지" loading="lazy" decoding="async" referrerpolicy="no-referrer"/></span>`;
}
function imageFallbackUrl() {
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="120" viewBox="0 0 160 120"><rect width="160" height="120" rx="12" fill="#eef4ff"/><rect x="44" y="20" width="72" height="50" rx="8" fill="#d9e6ff"/><path d="M54 58l16-18 13 12 10-9 15 15" fill="none" stroke="#526580" stroke-width="4"/><text x="80" y="96" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#526580">이미지 없음</text></svg>';
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

let previewTimer = null;
let previewPopover = null;
let previewTarget = null;

function ensurePreviewPopover() {
  if (previewPopover) return previewPopover;
  previewPopover = document.createElement('div');
  previewPopover.className = 'part-preview-popover';
  previewPopover.id = 'partImagePreview';
  previewPopover.setAttribute('role', 'tooltip');
  previewPopover.setAttribute('aria-hidden', 'true');
  previewPopover.innerHTML = '<div class="preview-image-wrap"><img alt="" referrerpolicy="no-referrer"><span class="preview-image-empty" hidden>대표 이미지가 없습니다</span></div><div class="preview-caption"><strong class="preview-name"></strong><span class="preview-price"></span><span class="preview-source"></span></div>';
  const img = previewPopover.querySelector('img');
  img.addEventListener('error', () => {
    if (retryProductImage(img)) return;
    img.hidden = true;
    previewPopover.querySelector('.preview-image-empty').hidden = false;
  });
  document.body.appendChild(previewPopover);
  return previewPopover;
}

function positionPreviewPopover(target, pop) {
  const rect = target.getBoundingClientRect();
  const margin = 12;
  const width = pop.offsetWidth || 260;
  const height = pop.offsetHeight || 300;
  let left = rect.right + margin;
  if (left + width > window.innerWidth - margin) left = rect.left - width - margin;
  left = Math.max(margin, Math.min(left, window.innerWidth - width - margin));
  const top = Math.max(margin, Math.min(rect.top, window.innerHeight - height - margin));
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;
}

function hidePartPreview() {
  clearTimeout(previewTimer);
  previewTimer = null;
  if (previewTarget) previewTarget.removeAttribute('aria-describedby');
  previewTarget = null;
  if (previewPopover) {
    previewPopover.classList.remove('show');
    previewPopover.setAttribute('aria-hidden', 'true');
  }
}

function schedulePartPreview(target) {
  hidePartPreview();
  if (!target?.dataset?.previewName) return;
  previewTimer = setTimeout(() => {
    if (!target.isConnected) return;
    const pop = ensurePreviewPopover();
    const img = pop.querySelector('img');
    const src = target.dataset.previewImage;
    img.hidden = !src;
    pop.querySelector('.preview-image-empty').hidden = Boolean(src);
    img.alt = `${target.dataset.previewName} 대표 이미지`;
    img.dataset.imageFallback = target.dataset.previewFallback || '';
    delete img.dataset.imageRetried;
    if (src) img.src = src;
    else img.removeAttribute('src');
    pop.querySelector('.preview-name').textContent = target.dataset.previewName;
    pop.querySelector('.preview-price').textContent = target.dataset.previewPrice || '가격 미확인';
    pop.querySelector('.preview-source').textContent = target.dataset.previewSource || '';
    positionPreviewPopover(target, pop);
    pop.classList.add('show');
    pop.setAttribute('aria-hidden', 'false');
    target.setAttribute('aria-describedby', pop.id);
    previewTarget = target;
  }, 220);
}

function bindPreviewTargets(root = document) {
  if (!root?.querySelectorAll) return;
  root.querySelectorAll('[data-preview-name]').forEach(node => {
    if (node.dataset.previewBound) return;
    node.dataset.previewBound = '1';
    node.addEventListener('mouseenter', () => schedulePartPreview(node));
    node.addEventListener('mouseleave', hidePartPreview);
    node.addEventListener('focusin', () => schedulePartPreview(node));
    node.addEventListener('focusout', hidePartPreview);
  });
  root.querySelectorAll('.product-thumb img, .part-thumb img, .cart-thumb img').forEach(img => {
    if (img.dataset.fallbackBound) return;
    img.dataset.fallbackBound = '1';
    const fallback = () => {
      if (retryProductImage(img)) return;
      img.hidden = true;
      img.parentElement.classList.remove('image-loading');
      img.parentElement.classList.add('image-unavailable');
      img.parentElement.setAttribute('aria-label', '대표 이미지 없음');
    };
    const loaded = () => {
      img.hidden = false;
      img.parentElement.classList.remove('image-unavailable', 'image-loading');
      img.parentElement.removeAttribute('aria-label');
    };
    img.addEventListener('error', fallback);
    img.addEventListener('load', loaded);
    if (img.complete) img.naturalWidth ? loaded() : fallback();
  });
}

function retryProductImage(img) {
  const fallback = img.dataset.imageFallback;
  if (!fallback || img.dataset.imageRetried || img.src === fallback) return false;
  img.dataset.imageRetried = '1';
  img.hidden = false;
  img.src = fallback;
  return true;
}

document.addEventListener('keydown', event => { if (event.key === 'Escape') hidePartPreview(); });
window.addEventListener('resize', hidePartPreview);
window.addEventListener('scroll', hidePartPreview, true);
