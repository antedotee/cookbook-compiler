// Scratch-style blocks. A custom Blockly generator turns them into recipe text (one-way: blocks -> text).
const Blocks = (() => {
  let workspace = null;
  const generator = new Blockly.CodeGenerator('Recipe');
  generator.INDENT = '';
  generator.scrub_ = (block, code, thisOnly) => {
    const next = block.nextConnection && block.nextConnection.targetBlock();
    return code + (next && !thisOnly ? generator.blockToCode(next) : '');
  };

  const insideRecipe = (block) => block.getRootBlock().type === 'recipe';
  const options = (names) => names.map((name) => [name, name]);

  function defineBlocks(vocab) {
    Blockly.common.defineBlocksWithJsonArray([
      {
        type: 'recipe',
        message0: 'RECIPE %1',
        args0: [{ type: 'field_dropdown', name: 'DISH', options: options(vocab.dishes) }],
        message1: '%1',
        args1: [{ type: 'input_statement', name: 'STEPS' }],
        colour: 20,
        tooltip: 'Start of a recipe. Put the steps inside.',
      },
      {
        type: 'add',
        message0: 'ADD %1 %2 of %3',
        args0: [
          { type: 'field_number', name: 'AMOUNT', value: 1, min: 0.01, max: vocab.max_amount, precision: 0.01 },
          { type: 'field_dropdown', name: 'UNIT', options: options(vocab.units) },
          { type: 'field_dropdown', name: 'INGREDIENT', options: options(vocab.ingredients) },
        ],
        previousStatement: null,
        nextStatement: null,
        colour: 120,
        tooltip: 'Add an ingredient to the pot.',
      },
      {
        type: 'cook',
        message0: '%1 for %2 minutes',
        args0: [
          { type: 'field_dropdown', name: 'VERB', options: options(vocab.cook_verbs) },
          { type: 'field_number', name: 'MINUTES', value: 1, min: vocab.min_minutes, max: vocab.max_minutes, precision: 0.5 },
        ],
        previousStatement: null,
        nextStatement: null,
        colour: 210,
        tooltip: 'Mix, boil, or bake what is in the pot.',
      },
      {
        type: 'serve',
        message0: 'SERVE',
        previousStatement: null,
        colour: 290,
        tooltip: 'The last step of every recipe.',
      },
    ]);

    generator.forBlock.recipe = (block) =>
      `RECIPE ${block.getFieldValue('DISH')};\n${generator.statementToCode(block, 'STEPS')}`;
    generator.forBlock.add = (block) => insideRecipe(block)
      ? `ADD(${block.getFieldValue('AMOUNT')}, ${block.getFieldValue('UNIT')}, ${block.getFieldValue('INGREDIENT')});\n` : '';
    generator.forBlock.cook = (block) => insideRecipe(block)
      ? `${block.getFieldValue('VERB')}(${block.getFieldValue('MINUTES')}, ${vocab.duration_unit});\n` : '';
    generator.forBlock.serve = (block) => insideRecipe(block) ? 'SERVE;\n' : '';
  }

  const add = (amount, unit, ingredient) => ({ type: 'add', fields: { AMOUNT: amount, UNIT: unit, INGREDIENT: ingredient } });
  const cook = (verb, minutes) => ({ type: 'cook', fields: { VERB: verb, MINUTES: minutes } });

  function chain(steps) {
    return steps.reduceRight((next, step) => (next ? { ...step, next: { block: next } } : step), null);
  }

  const STARTER_CAKE = {
    type: 'recipe', x: 20, y: 20, fields: { DISH: 'CAKE' },
    inputs: {
      STEPS: {
        block: chain([
          add(1, 'CUP', 'FLOUR'), add(1, 'CUP', 'FLOUR'), add(1, 'CUP', 'SUGAR'), add(2, 'PIECE', 'EGG'),
          add(1, 'CUP', 'MILK'), cook('MIX', 1), cook('MIX', 1), cook('BAKE', 30), { type: 'serve' },
        ]),
      },
    },
  };

  function init(vocab, onChange) {
    defineBlocks(vocab);
    workspace = Blockly.inject('blockly', {
      media: '/static/vendor/blockly/media/',
      toolbox: {
        kind: 'flyoutToolbox',
        contents: [
          { kind: 'block', type: 'recipe' },
          { kind: 'block', type: 'add', fields: { UNIT: 'CUP', INGREDIENT: 'FLOUR' } },
          { kind: 'block', type: 'add', fields: { AMOUNT: 2, UNIT: 'PIECE', INGREDIENT: 'EGG' } },
          { kind: 'block', type: 'cook' },
          { kind: 'block', type: 'serve' },
        ],
      },
      trashcan: true,
      zoom: { controls: true, startScale: 0.9 },
      move: { scrollbars: true, drag: true, wheel: true },
    });
    Blockly.serialization.workspaces.load({ blocks: { languageVersion: 0, blocks: [STARTER_CAKE] } }, workspace);
    workspace.addChangeListener((event) => {
      if (event.isUiEvent || event.type === Blockly.Events.FINISHED_LOADING) return;
      onChange(text());
    });
    return text();
  }

  function text() {
    return generator.workspaceToCode(workspace).trimEnd() + '\n';
  }

  return { init, text };
})();
