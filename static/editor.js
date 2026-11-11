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
      const ranges = merge(marks.errors.filter((e) => e.line === number)
        .map((e) => [Math.max(0, e.col - 1), Math.max(0, e.col - 1) + Math.max(1, e.length)]));
      if (!ranges.length) return el('div', { class: cls }, text || ' ');
      const padded = text.padEnd(ranges[ranges.length - 1][1], ' ');
      const parts = [];
      let at = 0;
      for (const [start, end] of ranges) {
        parts.push(padded.slice(at, start), el('mark', {}, padded.slice(start, end)));
        at = end;
      }
      parts.push(padded.slice(at));
      return el('div', { class: cls }, parts);
    }));
    gutter.replaceChildren(...lines.map((_, i) => el('div', {}, i + 1)));
    syncScroll();
  }

  function merge(ranges) {
    ranges.sort((a, b) => a[0] - b[0]);
    const out = [];
    for (const range of ranges) {
      const last = out[out.length - 1];
      if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
      else out.push([...range]);
    }
    return out;
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
