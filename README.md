# Digital Cookbook Compiler

A small compiler for a recipe language. You build a recipe from drag-and-drop blocks or type it, press **Compile**, and step through all six compiler phases in the browser.

```
RECIPE CAKE;
ADD(2, CUP, FLOUR);
MIX(2, MINUTES);
BAKE(30, MINUTES);
SERVE;
```

## Run it

You need Python 3.10 or newer. No internet is needed after the first install, because Blockly is included in `static/vendor/blockly`.

- macOS or Linux: `./run.sh`
- Windows: double-click `run.bat`

Each script creates a `.venv` folder on the first run, installs Flask, starts the server, and opens http://127.0.0.1:8000. Press Ctrl+C in the terminal to stop it.

To run it by hand instead: `python3 -m venv .venv`, `.venv/bin/pip install -r requirements.txt`, then `.venv/bin/python app.py`.

Run the tests with `.venv/bin/python -m pytest`.

## The language

```
recipe     = "RECIPE" IDENTIFIER ";" { step ";" } EOF ;
step       = "ADD" "(" CONSTANT "," IDENTIFIER "," IDENTIFIER ")"
           | ("MIX" | "BOIL" | "BAKE") "(" CONSTANT "," IDENTIFIER ")"
           | "SERVE" ;
CONSTANT   = digit { digit } [ "." digit { digit } ] ;
IDENTIFIER = letter { letter | digit | "_" } ;   (any name that is not a keyword)
```

The lexer sorts every token into one of four classes, the same ones the C standard uses.

| Class | Tokens |
|---|---|
| Keyword | RECIPE, ADD, MIX, BOIL, BAKE, SERVE |
| Identifier | dish, unit, and ingredient names such as CAKE, CUP, FLOUR |
| Constant | numbers such as 2 or 0.5 |
| Punctuator | `(` `)` `,` `;` |

Identifiers are not checked against the vocabulary until semantic analysis, just as a C lexer does not know whether a variable was declared. That is why a misspelling such as FLOWER is a phase 3 error with a "did you mean FLOUR?" hint, not a phase 1 error.

Keywords are not case-sensitive. A `#` starts a comment that runs to the end of the line.

| Kind | Values |
|---|---|
| Dishes | CAKE, PASTA, TEA |
| Ingredients | FLOUR, SUGAR, EGG, MILK, WATER, SALT, PASTA, TEA_LEAVES |
| Amount units | CUP, SPOON, PIECE (1 CUP = 16 SPOON) |
| Time unit | MINUTES, from 1 to 180 |

EGG is counted in whole PIECEs. Every other ingredient takes CUP or SPOON.

Each dish has a fixed order. Ingredients within one group can come in any order, and a cooking step can repeat back to back.

| Dish | Order |
|---|---|
| CAKE | add FLOUR, SUGAR, EGG, MILK, then MIX, then BAKE, then SERVE |
| PASTA | add WATER, then BOIL, then add PASTA, SALT, then BOIL, then SERVE |
| TEA | add WATER, then BOIL, then add TEA_LEAVES, MILK, then BOIL, then SERVE |

## The six phases

| Phase | File | Output | Example error |
|---|---|---|---|
| 1. Lexical analysis | `compiler/lexer.py` | token table with each token's class | `unexpected character '@'` |
| 2. Syntax analysis | `compiler/parser.py` | parse tree | `expected ';' after the BOIL step on line 4` |
| 3. Semantic analysis | `compiler/semantic.py` | rule checklist and symbol table | `EGG is measured in PIECE, not CUP` |
| 4. Intermediate code | `compiler/ir.py` | `t1 = add FLOUR, 1 CUP` | |
| 5. Optimization | `compiler/optimizer.py` | before, after, and a note per change | |
| 6. Target code | `compiler/codegen.py` | `PUT FLOUR, 32`, `MIX 120`, `HALT` | |

Phases 1 and 2 stop at the first error. Phase 3 reports every problem it finds. When a phase fails, the later phases are skipped.

The optimizer runs three passes in order. It converts amounts to base units (CUP to SPOON), merges back-to-back ADDs of the same ingredient, and merges back-to-back runs of the same cooking step. Steps that are not next to each other never merge, so PASTA keeps both of its BOILs.

The target machine has six instructions: `PUT <ingredient>, <spoons or pieces>`, `MIX <seconds>`, `BOIL <seconds>`, `BAKE <seconds>`, `SERVE`, and `HALT`. Each line ends with a comment naming the source lines it came from.

All cooking knowledge lives in `compiler/kitchen.py`. To add a dish or an ingredient, edit that file. The block dropdowns read the same table through `/api/vocab`.

## Project layout

- `app.py` is the Flask server. It serves the page and `/api/compile`, `/api/vocab`, and `/api/examples`.
- `compiler/pipeline.py` runs the six phases and builds the JSON the page shows.
- `compiler/model.py` holds the tokens, syntax tree nodes, and intermediate instructions passed between phases.
- `examples/` holds three valid recipes and one broken recipe for each of phases 1, 2, and 3.
- `static/` is the page. `blocks.js` defines the blocks and the generator that turns them into text. `phases.js` and `tree.js` draw each phase.
- `tests/` has tests for every phase, the API, and the examples.

## Five-minute demo

1. Start with `./run.sh`. The blocks hold a cake, and the recipe text below them was generated from those blocks.
2. Press **Compile**. Walk through the six tabs with **Next**. Point out the token table, the parse tree, the green checklist, the nine IR lines, the two merges in the optimizer, and the final eight machine instructions.
3. Drag the **SERVE** block out of the recipe. The text loses `SERVE;`. Compile again, and phase 3 fails with "the recipe must end with SERVE;".
4. Pick each broken example from the **Example** menu. Each one fails in its own phase, with the bad line marked in red and the later phases greyed out.
5. Type into the text box, for example change `CUP` to `PIECE` for FLOUR, and compile. Press **Reset from blocks** to go back to the block version.
