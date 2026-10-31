// Renders one phase's output into the main panel, and says which source lines it covers.
const Phases = (() => {
  const ABOUT = {
    lexer: 'The lexer reads characters and groups them into tokens. It skips spaces and # comments, and stops at the first character it does not know.',
    parser: 'The parser checks the tokens against the grammar and builds a parse tree. It stops at the first rule that does not match.',
    semantic: 'Semantic analysis checks meaning against the kitchen rules: known names, sensible units and amounts, and the dish\'s order. It reports every problem it finds.',
    ir: 'Intermediate code turns each step into one simple instruction, still in the units the recipe used.',
    optimizer: 'The optimizer rewrites amounts in base units, then merges back-to-back steps that do the same thing.',
    codegen: 'Code generation turns the optimized code into pseudo-assembly for a kitchen machine. Amounts are in spoons or pieces, times in seconds.',
  };

  const FIX = {
    lexer: 'Remove or replace the character. Recipes may only use letters, digits, _ . ( ) , ; and # comments.',
    parser: 'Each step looks like ADD(amount, unit, ingredient); or MIX(minutes, MINUTES); and ends with ;',
    semantic: 'Fix the lines marked in red, then press Compile again.',
  };

  function table(headers, rows) {
    return el('table', {},
      el('thead', {}, el('tr', {}, headers.map((h) => el('th', {}, h)))),
      el('tbody', {}, rows.map((row) => el('tr', {}, row.map((cell) => el('td', {}, cell))))));
  }

  function codeList(rows, cls) {
    return el('ol', { class: `code ${cls || ''}` }, rows.map((row) => el('li', {}, row.text)));
  }

  const render = {
    lexer: (out) => table(['#', 'Kind', 'Text', 'Line', 'Col'],
      out.tokens.map((t, i) => [i + 1, t.kind, t.text || '(end)', t.line, t.col])),

    parser: (out) => el('div', { class: 'tree-wrap' }, drawTree(out.tree)),

    semantic: (out) => el('div', {},
      el('h3', {}, 'Rule checklist'),
      el('ul', { class: 'checks' }, out.checks.map((c) =>
        el('li', { class: c.ok ? 'ok' : 'fail' }, el('span', { class: 'mark' }, c.ok ? '✓' : '✗'), c.message))),
      el('h3', {}, 'Symbol table'),
      table(['Name', 'Kind', 'Unit', 'Total', 'First line'],
        out.symbols.map((s) => [s.name, s.kind, s.unit, s.total, s.first_line]))),

    ir: (out) => codeList(out.code),

    optimizer: (out) => el('div', {},
      el('div', { class: 'columns' },
        el('div', {}, el('h3', {}, 'Before'), codeList(out.before)),
        el('div', {}, el('h3', {}, 'After'), codeList(out.after, 'after'))),
      el('h3', {}, 'What changed'),
      out.notes.length
        ? el('ul', { class: 'notes' }, out.notes.map((n) => el('li', {}, el('b', {}, n.pass), ' ', n.message)))
        : el('p', { class: 'hint' }, 'Nothing to optimize.')),

    codegen: (out) => el('pre', { class: 'asm' }, out.asm.map((row) => row.text).join('\n')),
  };

  function linesOf(phase) {
    const out = phase.output;
    if (!out) return [];
    switch (phase.id) {
      case 'lexer': return out.tokens.filter((t) => t.kind !== 'EOF').map((t) => t.line);
      case 'parser': return out.tree.lines;
      case 'semantic': return out.symbols.map((s) => s.first_line);
      case 'ir': return out.code.flatMap((row) => row.lines);
      case 'optimizer': return out.notes.flatMap((n) => n.lines);
      case 'codegen': return out.asm.flatMap((row) => row.lines);
      default: return [];
    }
  }

  function show(phase, failed) {
    const parts = [el('h2', {}, phase.title), el('p', { class: 'about' }, ABOUT[phase.id])];
    if (phase.status === 'error') {
      parts.push(el('div', { class: 'error-box' },
        phase.errors.map((e) => el('p', {}, el('b', {}, `Line ${e.line}, column ${e.col}: `), e.message)),
        FIX[phase.id] && el('p', { class: 'fix' }, FIX[phase.id])));
    }
    if (phase.status === 'skipped') {
      parts.push(el('p', { class: 'skipped' },
        `This phase did not run because ${failed ? failed.title : 'an earlier phase'} found an error. Fix it and press Compile again.`));
    }
    if (phase.output) parts.push(render[phase.id](phase.output));
    return el('div', {}, parts);
  }

  return { show, linesOf };
})();
