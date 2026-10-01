# Rescue Team Search: Depth-Limited Search (DLS)

## 1. Project title
**Searching Within a Limited Area: a Depth-Limited Search (DLS) demonstrator**

The main AI concept in this project is **Depth-Limited Search (DLS)**, a classical uninformed search algorithm.
The rescue scenario is only the example used to demonstrate it. The project uses **no machine-learning model**.

## 2. Problem statement
A rescue team is looking for a missing person in an area represented as connected locations. Due to limited
resources, the team can search only up to a specified number of levels from the starting location.
Develop a program to locate the target while respecting this limitation.

Suggested lab size: 10-15 locations, 15-20 connections, search depth limit 2-4.
(Default map here: **14 locations, 17 connections**, default depth limit 3.)

## 3. Aim
To implement and visualise Depth-Limited Search on a connected graph, so that a target is searched for
without ever exploring beyond a chosen depth.

## 4. Objectives
- Represent the map as an adjacency list.
- Implement DLS that enforces the depth limit strictly.
- Report three different outcomes clearly: **FOUND**, **CUTOFF** (target exists but is beyond the limit) and **NOT FOUND** (unreachable).
- Handle cycles, disconnected graphs and invalid input without crashing.
- Show the exploration step by step so that the algorithm can be understood and explained in a viva.

## 5. Concept used
- **Graph**: locations = nodes, roads = edges (undirected).
- **Depth**: number of edges between the start and a node (start = 0).
- **DFS**: follow one route as far as possible, then back up.
- **DLS = DFS + depth limit L**: a node at depth L is checked but never expanded.
- **Cut-off**: the special outcome meaning "not found *within the limit*" (different from "does not exist").

## 6. Features
- Default rescue map (14 places, 17 roads, cycles, one disconnected area) and a **custom graph editor**.
- Sidebar: algorithm, start, target, maximum depth (0-20), Search and Reset buttons.
- Graph picture: start, explored nodes (with depth), final path, target and nodes beyond the limit are colour-coded.
- Result box, path table, 8 statistics, full step log and a **replay slider** that redraws the map after each step.
- Built-in explanation of graph/node/edge/depth/DFS/DLS, a worked example that runs the real algorithm, and a BFS vs DFS vs DLS table.
- Input validation: empty graph, unknown start/target, self-loops, duplicate and invalid connections, negative depth.

## 7. Technology used
Python 3, Streamlit (UI and graph drawing through `st.graphviz_chart`, which needs no extra Python package),
standard library only for the algorithm and the tests (`dataclasses`, `collections`, `re`, `unittest`).

## 8. Algorithm
```
DLS(graph, start, target, L):
    best_depth = {}                       # node -> shallowest depth explored so far
    return VISIT(start, depth = 0, path = [])

VISIT(node, depth, path):
    if node in best_depth and best_depth[node] <= depth:  return FAIL      # cycle / duplicate
    best_depth[node] = depth
    path = path + [node]
    if node == target:                                    return path      # FOUND
    if depth == L:                                        return FAIL      # CUTOFF: do not go deeper
    for each neighbour of node:
        result = VISIT(neighbour, depth + 1, path)
        if result != FAIL:                                return result
    return FAIL
```
After a failed search, a breadth-first *diagnostic* (not part of the search) checks whether the target is connected
to the start at all, to choose between **CUTOFF** and **NOT FOUND**.

## 9. How the algorithm works
1. The start gets depth 0 and is checked against the target.
2. Each neighbour is explored one level deeper, depth-first.
3. A node at depth = L is checked but its neighbours are **not** explored. The code only recurses when `depth < L`,
   so no node deeper than L is ever created.
4. A node already explored at the same or a shallower depth is skipped, so cycles cannot cause endless loops.
   If a node is reached again by a **shorter** route it is explored again. A plain "visited set" would be wrong here:
   it could hide the target when a node was first reached near the limit by a long route (covered by a unit test).
5. When the target is found the recursion returns the path (start → ... → target).
6. If nothing is found: **CUTOFF** if the target is reachable but deeper than L, **NOT FOUND** if it is unreachable.

## 10. Project structure
```
rescue_dls/
├── app.py            Streamlit user interface (input and display only)
├── dls.py            depth_limited_search() and result classes (no UI code)
├── graph_data.py     default rescue map, graph building and validation
├── test_dls.py       25 unit tests (standard library unittest)
├── requirements.txt  streamlit>=1.30
├── README.md         this file
└── LAB_REPORT.md     university practical report + viva questions
```

## 11. Installation
```bash
cd rescue_dls
python -m venv venv                  # optional
source venv/bin/activate             # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 12. How to run
```bash
streamlit run app.py                 # opens http://localhost:8501
python -m unittest -v test_dls       # run the tests (no Streamlit needed)
```

## 13. Example
Default map, start **Base Camp**, target **Hospital**, depth limit **3**:

```
TARGET FOUND
Target: Hospital     Starting location: Base Camp     Search depth limit: 3
Path: Base Camp → Village → School → Hospital     Depth where found: 3     Nodes explored: 4
```
Same start, target **Police Station** (true distance 4), limit **3**:
```
TARGET NOT FOUND WITHIN DEPTH LIMIT (CUTOFF)
Reason: The target exists in the graph but cannot be reached within the specified search depth.
        It is 4 level(s) away from 'Base Camp', beyond the limit of 3.
```
Chain A - B - C - D, start A, target D, limit 2: A (depth 0), B (1), C (2). D would be at depth 3, so it is never
searched: **CUTOFF**.

## 14. Test cases
All are automated in `test_dls.py` (25 tests, all passing).

| # | Scenario | Input (default map) | Expected |
|---|----------|---------------------|----------|
| 1 | Found within limit | Base Camp → Hospital, L=3 | FOUND, path length 3 |
| 1b | Found at depth 2 | Base Camp → Market, L=2 | FOUND: Base Camp → Village → Market |
| 2 | Beyond the limit | Base Camp → Police Station, L=3 | CUTOFF (distance 4) |
| 2b | Same target, enough depth | Base Camp → Police Station, L=4 | FOUND, path length 4 |
| 3 | Unreachable | Base Camp → Mountain, L=0, 3, 10 | NOT FOUND every time |
| 4 | Start = target | Village → Village, L=0 | FOUND, path = [Village], 1 node explored |
| 5 | Depth limit 0 | Base Camp → Village, L=0 | CUTOFF, only Base Camp visited, 3 skipped |
| 5b | Depth limit 1 | Base Camp → School, L=1 | CUTOFF, max depth reached = 1 |
| 6 | Cycle | triangle A-B-C plus isolated Z, L=50 | terminates, NOT FOUND, visits A, B, C once |
| 7 | Shorter route re-explores | S-A, A-B, B-C, S-C, C-T, L=3 | FOUND via S → C → T |
| 8 | Random check | 300 random graphs | DLS finds target **iff** its true distance ≤ L; no explored node deeper than L; paths valid |
| 9 | Invalid input | empty graph, unknown start/target, L = -1, 2.5, "3" | INVALID_INPUT, no crash |
| 10 | Graph building | duplicates, self-loops, unknown places, blank text | warnings, no crash |

The UI was also run headlessly with Streamlit's `AppTest` for: the default search, CUTOFF, unreachable target,
start = target, depth 0, empty custom graph, custom graph with bad connections, and Reset. No exceptions occurred.

## 15. Expected results
- The graph picture always matches the log: no node in the picture is deeper than the depth limit.
- "Maximum depth reached" is never larger than "Search depth limit".
- CUTOFF results list the nodes that were not explored because of the limit.
- The search order is depth-first, so the path found is **not always the shortest** (unlike BFS).

## 16. Complexity analysis
With branching factor *b*, depth limit *L*, V nodes, E edges:

| Measure | Value |
|---------|-------|
| Time (tree view) | **O(b^L)** nodes generated in the worst case |
| Time (this implementation, graph with cycle check) | **O(L · (V + E))**: a node can be re-explored only when reached at a strictly smaller depth, so at most L + 1 times |
| Space | **O(V)** for the bookkeeping plus **O(L)** recursion stack (a pure tree DLS needs only O(b·L)) |
| Complete? | Only if the target lies within depth L |
| Optimal? | No (finds the first route, not the shortest) |

## 17. Applications
Search-and-rescue with a fixed search radius, game-tree search with a move limit, web crawlers with a link-depth
limit, network discovery within N hops, and as the inner loop of **Iterative Deepening DFS**.

## 18. Limitations
- Finds nothing beyond depth L, and a wrong L can miss a reachable target.
- Not optimal: the path can be longer than the shortest one.
- Edges are unweighted and undirected: distances, terrain and risk are ignored.
- The recursive implementation and the visualisation are meant for small graphs (the UI caps the depth at 20).

## 19. Future improvements
- Iterative Deepening DFS (increase L automatically) and a BFS comparison mode.
- Weighted edges (travel time) with a cost budget instead of a level budget.
- Several missing persons / several rescue teams; click-to-edit graph.
- Export the exploration log as CSV.

## 20. Conclusion
The project implements Depth-Limited Search as a real, tested algorithm. It enforces the depth limit strictly,
survives cycles and disconnected maps, and clearly separates FOUND, CUTOFF and NOT FOUND. The Streamlit interface shows
each step so that the behaviour of the depth limit can be seen and explained.
