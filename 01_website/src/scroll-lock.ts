/** Freeze the current scroll position without moving the document or changing its gutter. */
export function lockPageScroll() {
  const root = document.documentElement;
  const x = window.scrollX,
    y = window.scrollY;
  const properties = [
    'overflow',
    'touch-action',
    'overscroll-behavior',
    'scrollbar-gutter',
  ] as const;
  const saved = properties.map((name) => [
    name,
    root.style.getPropertyValue(name),
    root.style.getPropertyPriority(name),
  ]);
  root.style.setProperty('scrollbar-gutter', 'stable');
  root.style.setProperty('overflow', 'hidden');
  root.style.setProperty('touch-action', 'none');
  root.style.setProperty('overscroll-behavior', 'none');
  const stop = (event: Event) => {
    if (event.cancelable) event.preventDefault();
  };
  const keys = (event: KeyboardEvent) => {
    if (
      event.target instanceof HTMLElement &&
      event.target.closest('input, textarea, select, [contenteditable="true"]')
    )
      return;
    if (
      [
        'ArrowUp',
        'ArrowDown',
        'PageUp',
        'PageDown',
        'Home',
        'End',
        ' ',
      ].includes(event.key)
    )
      stop(event);
  };
  const restore = () => {
    if (window.scrollX !== x || window.scrollY !== y)
      window.scrollTo({ left: x, top: y, behavior: 'instant' });
  };
  document.addEventListener('wheel', stop, { passive: false, capture: true });
  document.addEventListener('touchmove', stop, {
    passive: false,
    capture: true,
  });
  document.addEventListener('keydown', keys, true);
  window.addEventListener('scroll', restore, { passive: true });
  let released = false;
  return () => {
    if (released) return;
    released = true;
    document.removeEventListener('wheel', stop, true);
    document.removeEventListener('touchmove', stop, true);
    document.removeEventListener('keydown', keys, true);
    window.removeEventListener('scroll', restore);
    for (const [name, value, priority] of saved) {
      if (value) root.style.setProperty(name, value, priority);
      else root.style.removeProperty(name);
    }
  };
}
