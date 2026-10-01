"""
graph_data.py - default rescue map and safe graph construction.

The graph is stored as an adjacency list: {location: [neighbouring locations]}.
All user-entered graphs go through build_graph(), which removes invalid data
(unknown locations, self-loops, duplicates ...) and reports warnings instead
of crashing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Graph = Dict[str, List[str]]

# ---------------------------------------------------------------------------
# Default rescue map: 14 locations, 17 connections
#   - Market is at depth 2 from Base Camp (reachable with a small limit)
#   - Hospital is at depth 3, Police Station at depth 4
#   - Mountain and Cave form a separate, disconnected area (unreachable)
#   - Several cycles exist (e.g. Base Camp - Forest - River)
# ---------------------------------------------------------------------------
DEFAULT_LOCATIONS: List[str] = [
    "Base Camp", "Village", "Forest", "River", "School", "Market", "Hill",
    "Bridge", "Hospital", "Temple", "Railway Station", "Police Station",
    "Mountain", "Cave",
]

DEFAULT_CONNECTIONS: List[Tuple[str, str]] = [
    ("Base Camp", "Village"),
    ("Base Camp", "Forest"),
    ("Base Camp", "River"),
    ("Village", "School"),
    ("Village", "Market"),
    ("Forest", "River"),
    ("Forest", "Hill"),
    ("River", "Bridge"),
    ("School", "Hospital"),
    ("Market", "Hospital"),
    ("Market", "Railway Station"),
    ("Hill", "Temple"),
    ("Bridge", "Temple"),
    ("Bridge", "Railway Station"),
    ("Hospital", "Police Station"),
    ("Railway Station", "Police Station"),
    ("Mountain", "Cave"),
]

DEFAULT_START = "Base Camp"
DEFAULT_TARGET = "Hospital"
DEFAULT_DEPTH = 3


@dataclass
class GraphBuild:
    """Result of building a graph: the graph, its unique edges and any warnings."""
    graph: Graph = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _clean(name) -> str:
    """Trim and collapse whitespace in a location name."""
    return " ".join(str(name).split())


def build_graph(locations, connections) -> GraphBuild:
    """
    Build an undirected adjacency-list graph.

    Ignored (with a warning): blank/duplicate locations, connections that use an
    unknown location, self-loops and duplicate connections.
    Location names are matched case-insensitively.
    """
    build = GraphBuild()
    canonical: Dict[str, str] = {}          # lower-case name -> spelling used in the graph

    for raw in locations:
        name = _clean(raw)
        if not name:
            continue
        if name.casefold() in canonical:
            build.warnings.append(f"Duplicate location '{name}' ignored.")
            continue
        canonical[name.casefold()] = name
        build.graph[name] = []

    for raw_a, raw_b in connections:
        a_raw, b_raw = _clean(raw_a), _clean(raw_b)
        a, b = canonical.get(a_raw.casefold()), canonical.get(b_raw.casefold())
        if a is None or b is None:
            unknown = a_raw if a is None else b_raw
            build.warnings.append(
                f"Invalid connection '{a_raw} - {b_raw}': '{unknown}' is not in the locations list.")
            continue
        if a == b:
            build.warnings.append(f"Self-loop '{a} - {b}' ignored (a place cannot connect to itself).")
            continue
        if b in build.graph[a]:
            build.warnings.append(f"Duplicate connection '{a} - {b}' ignored.")
            continue
        build.graph[a].append(b)
        build.graph[b].append(a)
        build.edges.append((a, b))

    return build


# ---- text input (custom graph editor) -------------------------------------
# Accepted separators between two locations:  "A - B"   "A, B"   "A -> B"   "A -- B"
_EDGE_SPLIT = re.compile(r"\s*(?:<->|->|--|–|—|,)\s*|\s+-\s+")


def parse_locations_text(text: str) -> List[str]:
    """Locations may be separated by new lines or commas."""
    names: List[str] = []
    for line in str(text).splitlines():
        names.extend(part for part in line.split(","))
    return [n for n in (_clean(x) for x in names) if n]


def parse_connections_text(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Parse one connection per line. Returns (pairs, warnings)."""
    pairs: List[Tuple[str, str]] = []
    warnings: List[str] = []
    for number, line in enumerate(str(text).splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = _EDGE_SPLIT.split(line)
        if len(parts) == 1 and line.count("-") == 1:      # "A-B" without spaces
            parts = line.split("-")
        parts = [_clean(p) for p in parts]
        if len(parts) != 2 or not all(parts):
            warnings.append(f"Line {number} ignored: '{line}' (expected 'Place A - Place B').")
            continue
        pairs.append((parts[0], parts[1]))
    return pairs, warnings


def graph_from_text(locations_text: str, connections_text: str) -> GraphBuild:
    pairs, parse_warnings = parse_connections_text(connections_text)
    build = build_graph(parse_locations_text(locations_text), pairs)
    build.warnings = parse_warnings + build.warnings
    return build


def default_graph() -> GraphBuild:
    return build_graph(DEFAULT_LOCATIONS, DEFAULT_CONNECTIONS)


def locations_to_text(locations) -> str:
    return "\n".join(locations)


def connections_to_text(connections) -> str:
    return "\n".join(f"{a} - {b}" for a, b in connections)
