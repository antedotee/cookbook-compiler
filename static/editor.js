// A textarea with line numbers and a highlight layer drawn behind it.
const Editor = (() => {
  const textarea = document.getElementById('source');
  const backdrop = document.getElementById('backdrop');
  const gutter = document.getElementById('gutter');
  let marks = { lines: new Set(), errors: [] };

  function render() {
    const lines = textarea.value.split('\n');
    const errorLines = new Set(marks.errors.map((e) => e.line));
    backdrop.replaceChildren(...lines.map((text, i) => {
      const number = i + 1;
      const cls = errorLines.has(number) ? 'line error' : marks.lines.has(number) ? 'line active' : 'line';
      const error = marks.errors.find((e) => e.line === number);
      if (!error) return el('div', { class: cls }, text || ' ');
      const start = Math.max(0, error.col - 1);
      const end = start + Math.max(1, error.length);
      const padded = text.padEnd(end, ' ');
      return el('div', { class: cls }, padded.slice(0, start), el('mark', {}, padded.slice(start, end)), padded.slice(end));
    }));
    gutter.replaceChildren(...lines.map((_, i) => el('div', {}, i + 1)));
    syncScroll();
  }

  function syncScroll() {
    backdrop.scrollTop = textarea.scrollTop;
    backdrop.scrollLeft = textarea.scrollLeft;
    gutter.scrollTop = textarea.scrollTop;
  }

  textarea.addEventListener('scroll', syncScroll);
  textarea.addEventListener('input', () => {
    marks = { lines: new Set(), errors: [] };
    render();
  });

  return {
    get text() { return textarea.value; },
    setText(text) {
      textarea.value = text;
      marks = { lines: new Set(), errors: [] };
      render();
    },
    highlight(lines, errors) {
      marks = { lines: new Set(lines), errors: errors || [] };
      render();
    },
    onInput(callback) { textarea.addEventListener('input', callback); },
  };
})();
