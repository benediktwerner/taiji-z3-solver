#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Any, Iterator, List, Optional

from z3 import (
    FreshBool,
    Solver,
    PbEq,
    sat,
    FreshInt,
    Or,
    And,
    ForAll,
    Implies,
    PbGe,
    If,
    Function,
    IntSort,
)

# format from https://github.com/sangchoo1201/taiji_maker/blob/master/src/file.py

DOT = [99999, 1, 2, 3, 4, 5, 6, 7, 8, 9, -9, -8, -7, -6, -5, -4, -3, -2, -1]
DIAMOND = 10
DASH = 11
SLASH = 12
FLOWER = [20, 21, 22, 23, 24]
NONE = 0
SYMBOLS = DOT[1:10] + DOT[-1:-10:-1] + [DIAMOND, DASH, SLASH, *FLOWER] + [NONE]
COLORS = "roygbpkw"

PRINT_CHARS = [".", "#"]


@dataclass
class Tile:
    color: Optional[str] = None
    symbol: int = NONE
    fixed: bool = False
    hidden: bool = False
    exist: bool = True
    lit: Any = None
    area: Any = None


def decode(data: str) -> List[List[Tile]]:
    width_s, data = data.split(":")
    width = int(width_s)
    data_l = data.split("+")
    data = data_l[0] + "".join(
        map(lambda x: "0" * (ord(x[0]) - 64) + x[1:] if x else x, data_l[1:])
    )
    data_l = data.split("-")
    data = data_l[0] + "".join(
        map(lambda x: "8" * (ord(x[0]) - 64) + x[1:] if x else x, data_l[1:])
    )
    result: List[List[Tile]] = [[]]
    i = 0
    while i < len(data):
        tile = Tile()
        if data[i] != "0":
            if data[i] in "<^/":
                print("connected tiles aren't supported")
                exit(1)
                # connected = {"^": (False, True), "<": (True, False), "/": (True, True)}[
                #     data[i]
                # ]
                # tile.connected[:3:2] = connected
                # connect(result, width, connected)
                # i += 1
            if 65 <= ord(data[i]) <= 90:
                tile.symbol = SYMBOLS[ord(data[i]) - 65]
                if tile.symbol in (SLASH, DASH):
                    print("dashes aren't supported")
                    exit(1)
                i += 1
            if data[i] in COLORS:
                tile.color = data[i]
                i += 1
            option = int(data[i])
            tile.exist = not bool(option & 0b1000)
            tile.fixed = bool(option & 0b100)
            tile.lit = bool(option & 0b10)
            tile.hidden = bool(option & 1)
        i += 1
        if len(result[-1]) == width:
            result.append([])
        result[-1].append(tile)
    return result


# def connect(grid, width, connected):
#     if len(grid[-1]) == width:
#         i, j = len(grid), 0
#     else:
#         i, j = len(grid) - 1, len(grid[-1])

#     if connected[0]:
#         grid[i][j - 1].connected[1] = True
#     if connected[1]:
#         grid[i - 1][j].connected[3] = True


def neighbors(x: int, y: int) -> Iterator[Tile]:
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx = x + dx
        ny = y + dy
        if 0 <= ny < height and 0 <= nx < width:
            tile = puzzle[ny][nx]
            if tile.exist:
                yield tile


puzzle = decode(input("Enter Taiji Maker puzzle code: "))

print("Setting up constraints...")

width = len(puzzle[0])
height = len(puzzle)

additional_edges = 2 * width + 2 * height
additional_vertecies = additional_edges
faces = FreshInt()
euler_pb = []

s = Solver()

for row in puzzle:
    for c in row:
        if c.exist:
            if not c.fixed:
                c.lit = FreshBool()
            c.area = FreshInt()
            s.add(c.area >= 0)
            s.add(c.area < faces)


for y, row in enumerate(puzzle):
    for x, c in enumerate(row):
        if not c.exist:
            continue

        if x > 0 and (n := puzzle[y][x - 1]).exist:
            euler_pb.append((c.lit != n.lit, -1))
            s.add((c.lit == n.lit) == (c.area == n.area))
        if y > 0 and (n := puzzle[y - 1][x]).exist:
            euler_pb.append((c.lit != n.lit, -1))
            s.add((c.lit == n.lit) == (c.area == n.area))

        if c.symbol in FLOWER:
            s.add(
                PbEq(
                    [(c.lit == n.lit, 1) for n in neighbors(x, y)],
                    FLOWER.index(c.symbol),
                )
            )


for y in range(height - 1):
    for x in range(width - 1):
        conds: List[Any] = []
        a, b, c, d = (
            puzzle[y + yd][x + xd] for xd, yd in ((0, 0), (1, 0), (0, 1), (1, 1))
        )
        if a.exist:
            if b.exist:
                conds.append(a.lit != b.lit)
            if c.exist:
                conds.append(a.lit != c.lit)
        if b.exist and d.exist:
            conds.append(b.lit != d.lit)
        if c.exist and d.exist:
            conds.append(c.lit != d.lit)

        if conds:
            euler_pb.append((Or(*conds), 1))


# v - e + f = 1  (vertecies, edges, faces, 1 instead of 2 bc we ignore the outer face)
euler_characteristic = (
    additional_vertecies
    - additional_edges
    + faces
    + sum(If(cond, val, 0) for cond, val in euler_pb)
)
s.add(euler_characteristic == 1)

# v - e + f = 1  (vertecies, edges, faces, 1 instead of 2 bc we ignore the outer face)
# v+v' -e-e' + f = 1 (split into additional and pb)
# v - e = 1 - f - v' + e
# this only works if faces is an int, could be used to brute-force faces
# s.add(PbEq(euler_pb, 1 - faces - additional_vertecies + additional_edges))

region = FreshInt()
region_valid = And(region >= 0, region < faces)
for_each_region = []

# Ensure that each region from 0 to faces exists (i.e. has a cell)
for_each_region.append(PbGe([(c.area == region, 1) for row in puzzle for c in row], 1))

# Dice
if any(c.symbol in DOT for row in puzzle for c in row):
    dice_sum = sum(
        If(c.area == region, c.symbol, 0) for row in puzzle for c in row if c.symbol in DOT
    )
    for_each_region.append(
        Or(
            sum(If(c.area == region, 1, 0) for row in puzzle for c in row) == dice_sum,
            dice_sum == 0,
        )
    )
    if len(set(c.color for row in puzzle for c in row)) > 1:
        region_dice_color = Function("f", IntSort(), IntSort())
        for row in puzzle:
            for c in row:
                if c.symbol != NONE and c.symbol in DOT and c.color:
                    s.add(region_dice_color(c.area) == COLORS.index(c.color))

s.add(ForAll([region], Implies(region_valid, And(*for_each_region),),))

# Diamonds
for row in puzzle:
    for c in row:
        if c.symbol == DIAMOND and c.color:
            s.add(
                PbEq(
                    [
                        (c.area == n.area, 1)
                        for row2 in puzzle
                        for n in row2
                        if n != c
                        and (
                            n.color == c.color
                            or (c.color == "p" and n.symbol in FLOWER[:-1])
                            or (c.color == "y" and n.symbol in FLOWER[1:])
                        )
                    ],
                    1,
                )
            )

print("Solving...")
result = s.check()
print(result)

if result == sat:
    model = s.model()
    for row in puzzle:
        line = []
        for c in row:
            if not c.exist:
                line.append(" ")
            elif c.fixed:
                line.append(PRINT_CHARS[c.lit])
            else:
                val = model[c.lit]
                if val is None:
                    line.append("~")
                else:
                    line.append(PRINT_CHARS[bool(val)])
        print("".join(line))
