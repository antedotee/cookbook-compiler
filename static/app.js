// Wires the page together: blocks -> text -> /api/compile -> phase strip with Next and Back.
(() => {
  const tabs = document.getElementById('tabs');
  const panel = document.getElementById('panel');
  const back = document.getElementById('back');
  const next = document.getElementById('next');
  const counter = document.getElementById('counter');
  const syncNote = document.getElementById('sync-note');
  const examples = document.getElementById('examples');

  const TAB_LABELS = ['1. Lexer', '2. Parser', '3. Semantic', '4. IR code', '5. Optimizer', '6. Target code'];
  let result = null;
  let current = 0;
  let editedByHand = false;

  function setEditedByHand(value) {
    editedByHand = value;
    syncNote.hidden = !value;
  }

  async function compile() {
    const response = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: Editor.text }),
    });
    const body = await response.json();
    if (!response.ok) {
      panel.replaceChildren(el('div', { class: 'error-box' }, body.error));
      return;
    }
    result = body;
    show(0);
  }

  function show(index) {
    current = index;
    const phases = result.phases;
    const phase = phases[index];
    const failed = phases.find((p) => p.status === 'error');

    tabs.replaceChildren(...phases.map((p, i) => {
      const tab = el('button', { class: `tab ${p.status}${i === index ? ' current' : ''}`, title: p.title }, TAB_LABELS[i]);
      tab.addEventListener('click', () => show(i));
      return tab;
    }));
    panel.replaceChildren(Phases.show(phase, failed));
    panel.scrollTop = 0;
    Editor.highlight(Phases.linesOf(phase), failed ? failed.errors : []);

    back.disabled = index === 0;
    next.disabled = index === phases.length - 1;
    counter.textContent = `Phase ${index + 1} of ${phases.length}`;
  }

  function renderEmptyTabs() {
    tabs.replaceChildren(...TAB_LABELS.map((label) => el('button', { class: 'tab skipped', disabled: '' }, label)));
  }

  async function loadExamples() {
    const list = await (await fetch('/api/examples')).json();
    for (const example of list) examples.append(el('option', { value: example.id }, example.title));
    examples.addEventListener('change', () => {
      const chosen = list.find((e) => e.id === examples.value);
      if (!chosen) return;
      Editor.setText(chosen.source);
      setEditedByHand(true);
      compile();
    });
  }

  async function start() {
    renderEmptyTabs();
    const vocab = await (await fetch('/api/vocab')).json();
    Editor.setText(Blocks.init(vocab, (text) => {
      if (!editedByHand) Editor.setText(text);
    }));
    Editor.onInput(() => setEditedByHand(true));
    document.getElementById('reset-from-blocks').addEventListener('click', () => {
      Editor.setText(Blocks.text());
      setEditedByHand(false);
      examples.value = '';
    });
    document.getElementById('compile').addEventListener('click', compile);
    back.addEventListener('click', () => result && show(current - 1));
    next.addEventListener('click', () => result && show(current + 1));
    await loadExamples();
  }

  start();
})();
