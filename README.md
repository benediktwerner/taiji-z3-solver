# z3-based Taiji solver

## Requirements:
- Python 3.7+
- z3: `pip install z3`

## Usage
- `python3 solver.py`
- Paste Taiji Maker puzzle code and press enter
- May take a while (few minutes for medium sized puzzles, probably much longer for large ones)

## How it works
- Each cell has a z3 Bool to determine whether it's on or off and a z3 Int to determin the area it's in
- Flower constraints are trivial constraint that number of neighbors with n.lit != flower.lit is equal to the yellow petals
- For all neighboring cells, enforce a.area == b.area <=> a.lit == b.lit
- But this allows disconnected areas getting assigned the same number i.e. being considered the same
- To solve this, we create a z3 Int for number of areas
  - Constrained by Euler characteristic (vertecies - edges + faces = 1)
  - Put vertex at each cell corner along an area border
  - Number of edges: sum of If(a.lit != b.lit, 1, 0) for all neighboring cells + fixed number of edges towards the outside
  - Number of vertecies: similar but instead check for each corner if any of the four neighboring cells that share a border don't have the same state
- Then we can enforce that there exist that many different area values (or rather, that there exists at least one cell with each area value from 0 to the number of areas) which automatically enforces that each area has a unique number
- For dice:
  - Now trivial: constrain that for each region the number of cells in it equals the number of dice pips
  - If different colored dice exist, also define a z3 function f that assigns each area a color (just an int, corresponding to the index of the color) and enforce that f(dice.area) == dice.color for all dice
- For diamonds:
  - Now also trivial: enforce that the number of cells with the same color and area as the diamond equals one