"""
dls.py - Depth-Limited Search (DLS) for the rescue-team problem.

This module contains ONLY the search logic (no Streamlit / UI code), so it can
be tested and reused on its own.

Graph format (adjacency list):
    {"Base Camp": ["Village", "Forest"], "Village": ["Base Camp"], ...}

Main function:
    depth_limited_search(graph, start, target, depth_limit) -> SearchResult

Outcomes (SearchResult.status):
    FOUND          target reached at depth <= depth_limit
    CUTOFF         target exists, but lies deeper than depth_limit
    NOT_FOUND      target is unreachable (not connected to the start at all)
    INVALID_INPUT  bad input (empty graph, unknown start/target, bad limit ...)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

Graph = Dict[str, List[str]]

# ---- result statuses -------------------------------------------------------
FOUND = "FOUND"
CUTOFF = "CUTOFF"
NOT_FOUND = "NOT_FOUND"
INVALID_INPUT = "INVALID_INPUT"

# ---- step actions (used in the step-by-step log) ---------------------------
EXPAND = "EXPAND"   # node visited and its neighbours are explored next
GOAL = "GOAL"       # node is the target -> search stops
LIMIT = "LIMIT"     # node is at the depth limit -> its neighbours are NOT explored
SKIP = "SKIP"       # node was already explored at the same/shallower depth


@dataclass
class Step:
    """One line of the exploration log (one call of the recursive function)."""
    number: int
    node: str
    depth: int
    parent: Optional[str]
    action: str
    detail: str
    skipped_neighbors: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Everything the UI needs to explain what DLS did."""
    status: str
    start: str
    target: str
    depth_limit: int
    path: List[str] = field(default_factory=list)          # start ... target (if found)
    visited_order: List[str] = field(default_factory=list)  # distinct nodes, first-visit order
    depth_of: Dict[str, int] = field(default_factory=dict)  # shallowest depth each node was explored at
    steps: List[Step] = field(default_factory=list)
    skipped_by_limit: List[str] = field(default_factory=list)  # nodes never explored because of the limit
    cutoff_nodes: List[str] = field(default_factory=list)      # nodes at the limit that had unexplored neighbours
    max_depth_reached: int = 0
    expansions: int = 0                     # number of times a node was (re)explored
    target_distance: Optional[int] = None   # true shortest distance (diagnostic only)
    reason: str = ""

    @property
    def found(self) -> bool:
        return self.status == FOUND

    @property
    def nodes_explored(self) -> int:
        return len(self.visited_order)

    @property
    def path_length(self) -> Optional[int]:
        """Number of connections on the path (None if no path)."""
        return len(self.path) - 1 if self.path else None


def format_path(path: List[str], separator: str = " → ") -> str:
    return separator.join(path)


def shortest_distance(graph: Graph, start: str, target: str) -> Optional[int]:
    """
    Plain BFS used ONLY as a *diagnostic after the search* so the program can
    explain WHY the target was not found (beyond the limit vs. unreachable).
    It never influences how DLS explores the graph.
    """
    if start not in graph or target not in graph:
        return None
    distance = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == target:
            return distance[node]
        for neighbour in graph.get(node, []):
            if neighbour in graph and neighbour not in distance:
                distance[neighbour] = distance[node] + 1
                queue.append(neighbour)
    return None


def _input_error(graph, start, target, depth_limit) -> Optional[str]:
    """Return an error message for invalid input, or None if everything is fine."""
    if not isinstance(graph, dict):
        return "The graph must be an adjacency list (a dictionary)."
    if len(graph) == 0:
        return "The graph is empty. Add at least one location."
    if not isinstance(start, str) or start not in graph:
        return f"Starting location '{start}' does not exist in the graph."
    if not isinstance(target, str) or target not in graph:
        return f"Target location '{target}' does not exist in the graph."
    if isinstance(depth_limit, bool) or not isinstance(depth_limit, int):
        return "The depth limit must be a whole number."
    if depth_limit < 0:
        return "The depth limit cannot be negative."
    return None


def depth_limited_search(graph: Graph, start: str, target: str, depth_limit: int) -> SearchResult:
    """
    Depth-Limited Search (recursive depth-first search with a depth cut-off).

    * The start location has depth 0; every step away from it adds 1.
    * A location at depth == depth_limit is still checked (it may be the target)
      but its neighbours are NEVER explored, so nothing deeper than the limit
      is ever visited.
    * Cycles: `best_depth` remembers the shallowest depth at which each node
      was explored. A node is skipped if it was already explored at the same or
      a shallower depth (this stops infinite loops). If it is reached again by a
      SHORTER route it is explored again - this matters because a plain
      "visited set" could wrongly hide the target when a node was first reached
      near the depth limit through a long route.

    Returns a SearchResult (never just True/False, never raises on bad input).
    """
    error = _input_error(graph, start, target, depth_limit)
    if error:
        return SearchResult(INVALID_INPUT, str(start), str(target),
                            depth_limit if isinstance(depth_limit, int) else -1,
                            reason=error)

    best_depth: Dict[str, int] = {}          # node -> shallowest depth explored so far
    visited_order: List[str] = []
    steps: List[Step] = []
    limit_pending: Dict[str, List[str]] = {}  # node at limit -> neighbours it could not explore
    counters = {"expansions": 0}

    def log(node, depth, parent, action, detail, skipped=None):
        steps.append(Step(len(steps) + 1, node, depth, parent, action, detail, skipped or []))

    def visit(node: str, depth: int, parent: Optional[str], path: List[str]) -> Optional[List[str]]:
        """Explore `node` at `depth`. Returns the path to the target, or None."""
        # 1) Cycle / duplicate guard.
        if node in best_depth and best_depth[node] <= depth:
            log(node, depth, parent, SKIP,
                f"Already explored at depth {best_depth[node]} (<= {depth}); skipped (cycle / duplicate).")
            return None

        # 2) Mark as explored at this depth.
        if node not in best_depth:
            visited_order.append(node)
        best_depth[node] = depth
        counters["expansions"] += 1
        path = path + [node]

        # 3) Goal test.
        if node == target:
            log(node, depth, parent, GOAL, f"Target found at depth {depth}.")
            return path

        neighbours = list(dict.fromkeys(n for n in graph.get(node, []) if n in graph))

        # 4) Depth limit: do NOT go deeper.
        if depth == depth_limit:
            pending = [n for n in neighbours if n not in best_depth]
            limit_pending[node] = pending
            if pending:
                log(node, depth, parent, LIMIT,
                    f"Depth limit {depth_limit} reached. Not exploring {', '.join(pending)} "
                    f"(depth {depth + 1} is beyond the limit).", pending)
            else:
                log(node, depth, parent, LIMIT,
                    f"Depth limit {depth_limit} reached. No unexplored neighbours, nothing skipped.")
            return None

        # 5) Otherwise explore each neighbour one level deeper (depth-first).
        shown = ", ".join(neighbours) if neighbours else "none"
        log(node, depth, parent, EXPAND, f"Exploring {node}. Neighbours: {shown}.")
        for neighbour in neighbours:
            found_path = visit(neighbour, depth + 1, node, path)
            if found_path is not None:
                return found_path
        return None

    try:
        path = visit(start, 0, None, [])
    except RecursionError:
        return SearchResult(INVALID_INPUT, start, target, depth_limit,
                            reason="The graph is too deep for the recursive implementation.")

    # ---- collect statistics -------------------------------------------------
    skipped: List[str] = []
    cutoff_nodes: List[str] = []
    for node, pending in limit_pending.items():
        if best_depth[node] != depth_limit:      # later re-explored at a shallower depth
            continue
        still_unexplored = [n for n in pending if n not in best_depth]
        if still_unexplored:
            cutoff_nodes.append(node)
        for n in still_unexplored:
            if n not in skipped:
                skipped.append(n)

    result = SearchResult(
        status=NOT_FOUND, start=start, target=target, depth_limit=depth_limit,
        path=path or [], visited_order=visited_order, depth_of=dict(best_depth),
        steps=steps, skipped_by_limit=skipped, cutoff_nodes=cutoff_nodes,
        max_depth_reached=max(best_depth.values()), expansions=counters["expansions"],
    )

    # ---- classify the outcome ----------------------------------------------
    if path is not None:
        result.status = FOUND
        if start == target:
            result.reason = "The starting location is the target (depth 0)."
        else:
            result.reason = f"'{target}' was found at depth {len(path) - 1}, within the limit of {depth_limit}."
        return result

    # Not found: use a post-search reachability check to explain why.
    result.target_distance = shortest_distance(graph, start, target)
    if result.target_distance is None:
        result.status = NOT_FOUND
        result.reason = (f"'{target}' is not connected to '{start}' by any chain of connections, "
                         f"so no depth limit could reach it (unreachable).")
    else:
        result.status = CUTOFF
        result.reason = (f"The target exists in the graph but cannot be reached within the specified "
                         f"search depth. It is {result.target_distance} level(s) away from '{start}', "
                         f"beyond the limit of {depth_limit}. Use a limit of at least "
                         f"{result.target_distance} to find it.")
    return result
