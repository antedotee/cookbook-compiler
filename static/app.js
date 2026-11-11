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
  let latestRequest = 0;

  function setEditedByHand(value) {
    editedByHand = value;
    syncNote.hidden = !value;
  }

  async function compile() {
    const request = ++latestRequest;
    const source = Editor.text;
    let body;
    try {
      const response = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      const isJson = (response.headers.get('content-type') || '').includes('application/json');
      body = isJson ? await response.json() : { error: `The server answered ${response.status}. Check the terminal running app.py.` };
      if (!response.ok) throw new Error(body.error);
    } catch (error) {
      if (request !== latestRequest) return;
      clearResult();
      panel.replaceChildren(el('div', { class: 'error-box' }, error.message || 'Could not reach the server. Is app.py running?'));
      return;
    }
    if (request !== latestRequest || source !== Editor.text) return;
    result = body;
    show(0);
  }

  // The result belongs to the text it was compiled from. Once the text changes it is out of date.
  function clearResult(message) {
    result = null;
    renderEmptyTabs();
    Editor.highlight([], []);
    counter.textContent = '';
    back.disabled = next.disabled = true;
    panel.replaceChildren(el('p', { class: 'hint' }, message || ''));
  }

  function textChanged() {
    latestRequest++;
    if (result) clearResult('The recipe changed. Press Compile to run the phases again.');
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
      textChanged();
      setEditedByHand(true);
      examples.value = '';
      compile();
    });
  }

  async function start() {
    renderEmptyTabs();
    let vocab;
    try {
      vocab = await (await fetch('/api/vocab')).json();
    } catch (error) {
      panel.replaceChildren(el('div', { class: 'error-box' }, 'Could not reach the server. Start it with run.sh or run.bat.'));
      return;
    }
    Editor.setText(Blocks.init(vocab, (text) => {
      if (editedByHand || text === Editor.text) return;
      Editor.setText(text);
      textChanged();
    }));
    Editor.onInput(() => {
      setEditedByHand(true);
      textChanged();
    });
    document.getElementById('reset-from-blocks').addEventListener('click', () => {
      Editor.setText(Blocks.text());
      textChanged();
      setEditedByHand(false);
    });
    document.getElementById('compile').addEventListener('click', compile);
    back.addEventListener('click', () => result && show(current - 1));
    next.addEventListener('click', () => result && show(current + 1));
    await loadExamples();
  }

  start();
})();
