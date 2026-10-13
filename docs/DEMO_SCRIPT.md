# Demo script (about 8 minutes)

Open `demo/index.html` in a browser before you start, full screen, light mode. Keep the numbers below on a card. Every one comes from `results/`.

Say the lines in your own words. The text in quotes is a guide, not something to read out.

## 0. Setup (before the guide walks in)

- Run `.venv\Scripts\python.exe -m pytest -q` once so you can say "90 tests pass" truthfully.
- Open the demo on the Overview tab.
- Have `paper/paper.docx` and `docs/CP_Project_Review.pptx` closed but ready.

## 1. The problem (1 min), Overview tab

"TAPE builds a graph from several candidate plans and a solver picks the path. It has two weak points. It never checks a move against the game's rules, and it uses the same solver for everything. We added a layer for that. You told us not to use a language model, so every proposer here is an ordinary program."

Point at the flow diagram: Propose, Merge, Check, Choose, Run, and the replan loop. Say that Check and Choose are ours.

## 2. Safety (1.5 min), River tab

"This is River Crossing, three missionaries and three cannibals. Our environment accepts every move, even unsafe ones."

- Choose Plan A (the unsafe plan) and press Play. It reaches the far bank.
- Say: "It reached the goal but broke the safety rule on the way. A pipeline that checks only legality calls this a success."
- Switch to Plan B or turn the checker on. Say: "Same game, safe success goes from 0% to 100%."

## 3. Search saved by pruning (1.5 min), Sokoban then Boxoban

"In Sokoban one push into a corner ends the level. The checker rejects that push before the search wastes time on it."

On Boxoban: "These are 3,000 public levels. At 30,000 nodes the hard set goes from 54% solved to 82%. It never lost a level the plain search solved. Dead-corner pruning is standard in Sokoban solvers, so we claim only that our validator works as that pruner on levels we did not write."

## 4. Harder games (2 min), Peg, 24-Puzzle, Rubik's Cube tabs

- **Peg Solitaire:** "The checker is a pagoda function, a proof that the goal is out of reach. From the real start it cuts the search from 139,048 to 82,009 nodes."
  In the run panel, show "A slip" first, then "A wrong move". Say: "With the checker the dead end costs 16,978 nodes, without it 38,920."
- **24-Puzzle:** press Randomize. "Weighted A* solves 20-move scrambles every time and 80-move scrambles 57% of the time. If I give it an unsolvable start, the parity check stops it after one node. Without it, 60,000 nodes are wasted."
- **Rubik's Cube:** press Randomize and drag to rotate it. "Meet in the middle solves every scramble of 4 to 8 moves. A twisted corner is rejected at once. Without the check it burns 400,000 nodes."

## 5. Honest results (1 min), Results tab

Say these without being asked, because the guide will respect it:

- "Choosing A* for single-piece games cut planning time from 51.8 ms to 7.6 ms. On two-box Sokoban and Rush Hour it did nothing."
- "The experience store reduced replans on one-box Sokoban and River Crossing, by about 14%. On Rush Hour and two-box Sokoban it did not."
- "Tuning the cost weights found nothing better than our defaults. Plan merging never produced a shorter path."
- "Depth-first search beat weighted A* on Peg Solitaire, 10,845 nodes against 139,048. AO* reduces to A* on deterministic games, so we did not build it."

## 6. Limits and close (1 min)

"We never tested a language model, so we say nothing about how real model errors behave. The next test is a learned proposer on Boxoban."

Hand over: paper (5 pages, IEEE format), review deck, repo link https://github.com/Harsh-v69/MachineLearningCP.

## Likely questions

- **Why no language model?** "Guide's decision. It also let us repeat every run from a seed and control plan quality, which a model would not."
- **Is the checker new?** "Dead-corner pruning is not. The pagoda checker on Peg Solitaire, the parity and cubie checks, and the River safety rule are per-game validators we wrote. The point is the shared interface, so a new game needs one checker."
- **Does it beat TAPE?** "We can't compare. TAPE's benchmarks need a language model."
- **Why did tuning fail?** "The best training point scored 3.906 against 4.219 for the defaults, but on unseen seeds it was 0.122 worse. The default weights are not provably optimal, we just found nothing better."
- **Who did what?** See the team slide and section 22 of `progress.md`.

## If something breaks

- Demo will not load: run `python -m http.server 8000` inside the `demo` folder and open `http://localhost:8000`.
- Animation stalls: switch tabs and back, or press Reset.
- Last resort: show the review deck, which has the same flow and numbers.
