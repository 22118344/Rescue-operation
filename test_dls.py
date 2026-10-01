"""
test_dls.py - tests for dls.py and graph_data.py (standard library only).

Run with:   python -m unittest -v test_dls
       or:  python test_dls.py
"""

import random
import unittest

from dls import CUTOFF, FOUND, INVALID_INPUT, NOT_FOUND, depth_limited_search, shortest_distance
from graph_data import (build_graph, default_graph, graph_from_text, parse_connections_text)


def make_graph(edges, extra_nodes=()):
    """Helper: build an undirected adjacency list from (a, b) pairs."""
    nodes = list(dict.fromkeys([n for e in edges for n in e] + list(extra_nodes)))
    return build_graph(nodes, edges).graph


DEFAULT = default_graph().graph


class RequiredScenarios(unittest.TestCase):
    """The six scenarios from the project specification."""

    def test_1_target_found_within_limit(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "Hospital", 3)
        self.assertEqual(r.status, FOUND)
        self.assertEqual(r.path, ["Base Camp", "Village", "School", "Hospital"])
        self.assertEqual(r.path_length, 3)
        self.assertLessEqual(r.max_depth_reached, 3)

    def test_1b_target_at_depth_two(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "Market", 2)
        self.assertEqual(r.status, FOUND)
        self.assertEqual(r.path, ["Base Camp", "Village", "Market"])

    def test_2_target_beyond_limit(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "Police Station", 3)   # real distance = 4
        self.assertEqual(r.status, CUTOFF)
        self.assertEqual(r.path, [])
        self.assertEqual(r.target_distance, 4)
        self.assertLessEqual(r.max_depth_reached, 3)
        self.assertNotIn("Police Station", r.visited_order)
        self.assertIn("Police Station", r.skipped_by_limit)

    def test_2b_same_target_found_when_limit_is_enough(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "Police Station", 4)
        self.assertEqual(r.status, FOUND)
        self.assertEqual(r.path_length, 4)

    def test_3_target_unreachable(self):
        for limit in (0, 3, 10):
            r = depth_limited_search(DEFAULT, "Base Camp", "Mountain", limit)
            self.assertEqual(r.status, NOT_FOUND, f"limit={limit}")
            self.assertEqual(r.path, [])
            self.assertIsNone(r.target_distance)

    def test_4_start_equals_target(self):
        for limit in (0, 1, 3):
            r = depth_limited_search(DEFAULT, "Village", "Village", limit)
            self.assertEqual(r.status, FOUND)
            self.assertEqual(r.path, ["Village"])
            self.assertEqual(r.path_length, 0)
            self.assertEqual(r.nodes_explored, 1)

    def test_5_depth_limit_zero(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "Village", 0)
        self.assertEqual(r.status, CUTOFF)
        self.assertEqual(r.visited_order, ["Base Camp"])       # only the start is looked at
        self.assertEqual(r.max_depth_reached, 0)
        self.assertEqual(r.skipped_by_limit, ["Village", "Forest", "River"])

    def test_5b_depth_limit_one(self):
        r = depth_limited_search(DEFAULT, "Base Camp", "School", 1)
        self.assertEqual(r.status, CUTOFF)
        self.assertEqual(set(r.visited_order), {"Base Camp", "Village", "Forest", "River"})
        self.assertEqual(r.max_depth_reached, 1)

    def test_6_graph_with_cycle_terminates(self):
        cycle = make_graph([("A", "B"), ("B", "C"), ("C", "A")])
        r = depth_limited_search(cycle, "A", "C", 5)
        self.assertEqual(r.status, FOUND)
        cycle2 = make_graph([("A", "B"), ("B", "C"), ("C", "A")], extra_nodes=["Z"])
        r2 = depth_limited_search(cycle2, "A", "Z", 50)           # would loop forever without a cycle guard
        self.assertEqual(r2.status, NOT_FOUND)
        self.assertEqual(sorted(r2.visited_order), ["A", "B", "C"])


class DepthLimitIsReallyEnforced(unittest.TestCase):

    def test_node_first_reached_deep_is_still_found_via_shorter_route(self):
        # S-A, A-B, B-C, S-C, C-T.  With limit 3 the DFS first reaches C at depth 3
        # (S->A->B->C).  A naive global 'visited' set would then skip C on the short
        # route S->C and miss T (distance 2).  Our best-depth check must find it.
        g = make_graph([("S", "A"), ("A", "B"), ("B", "C"), ("S", "C"), ("C", "T")])
        r = depth_limited_search(g, "S", "T", 3)
        self.assertEqual(r.status, FOUND)
        self.assertEqual(r.path, ["S", "C", "T"])

    def test_chain_example_from_the_lab_sheet(self):
        chain = make_graph([("A", "B"), ("B", "C"), ("C", "D")])
        r = depth_limited_search(chain, "A", "D", 2)
        self.assertEqual(r.status, CUTOFF)
        self.assertEqual(r.depth_of, {"A": 0, "B": 1, "C": 2})
        self.assertEqual(r.skipped_by_limit, ["D"])
        self.assertEqual(depth_limited_search(chain, "A", "D", 3).status, FOUND)

    def test_step_log_never_goes_past_limit(self):
        for limit in range(0, 6):
            r = depth_limited_search(DEFAULT, "Base Camp", "Cave", limit)
            self.assertTrue(all(s.depth <= limit for s in r.steps))
            self.assertTrue(all(d <= limit for d in r.depth_of.values()))

    def test_random_graphs_agree_with_bfs(self):
        """DLS finds the target  <=>  its true distance is <= limit (300 random graphs)."""
        rng = random.Random(42)
        for _ in range(300):
            n = rng.randint(1, 9)
            nodes = [f"N{i}" for i in range(n)]
            edges = [(a, b) for a in nodes for b in nodes if a < b and rng.random() < 0.3]
            graph = build_graph(nodes, edges).graph
            start, target, limit = rng.choice(nodes), rng.choice(nodes), rng.randint(0, 6)
            r = depth_limited_search(graph, start, target, limit)
            dist = shortest_distance(graph, start, target)

            self.assertEqual(r.status == FOUND, dist is not None and dist <= limit)
            if dist is None:
                self.assertEqual(r.status, NOT_FOUND)
            elif dist > limit:
                self.assertEqual(r.status, CUTOFF)
            self.assertTrue(all(d <= limit for d in r.depth_of.values()))
            if r.status == FOUND:
                self.assertEqual(r.path[0], start)
                self.assertEqual(r.path[-1], target)
                self.assertLessEqual(len(r.path) - 1, limit)
                self.assertEqual(len(set(r.path)), len(r.path))              # no repeated node
                for a, b in zip(r.path, r.path[1:]):
                    self.assertIn(b, graph[a])                               # every hop is a real edge


class InvalidInput(unittest.TestCase):

    def test_empty_graph(self):
        self.assertEqual(depth_limited_search({}, "A", "B", 2).status, INVALID_INPUT)

    def test_unknown_start_and_target(self):
        self.assertEqual(depth_limited_search(DEFAULT, "Atlantis", "Hospital", 2).status, INVALID_INPUT)
        self.assertEqual(depth_limited_search(DEFAULT, "Base Camp", "Atlantis", 2).status, INVALID_INPUT)

    def test_bad_depth_limit(self):
        for bad in (-1, 2.5, "3", None, True):
            self.assertEqual(depth_limited_search(DEFAULT, "Base Camp", "Hospital", bad).status, INVALID_INPUT)

    def test_bad_graph_type(self):
        self.assertEqual(depth_limited_search(None, "A", "B", 1).status, INVALID_INPUT)

    def test_very_small_graphs(self):
        one = make_graph([], extra_nodes=["Solo"])
        self.assertEqual(depth_limited_search(one, "Solo", "Solo", 0).status, FOUND)
        two = make_graph([("A", "B")])
        self.assertEqual(depth_limited_search(two, "A", "B", 1).status, FOUND)
        self.assertEqual(depth_limited_search(two, "A", "B", 0).status, CUTOFF)

    def test_raw_graph_with_dangling_neighbour_does_not_crash(self):
        raw = {"A": ["B", "GHOST"], "B": ["A"]}
        self.assertEqual(depth_limited_search(raw, "A", "B", 2).status, FOUND)


class GraphBuilding(unittest.TestCase):

    def test_default_graph_matches_specification(self):
        b = default_graph()
        self.assertEqual(len(b.graph), 14)          # 10-15 locations
        self.assertEqual(len(b.edges), 17)          # 15-20 connections
        self.assertEqual(b.warnings, [])
        self.assertIsNone(shortest_distance(b.graph, "Base Camp", "Mountain"))   # disconnected part
        self.assertEqual(shortest_distance(b.graph, "Base Camp", "Market"), 2)
        self.assertEqual(shortest_distance(b.graph, "Base Camp", "Police Station"), 4)

    def test_invalid_duplicate_and_self_loop_connections(self):
        b = build_graph(["A", "B", "C"], [("A", "B"), ("B", "A"), ("A", "A"), ("A", "X"), ("a", "c")])
        self.assertEqual(b.edges, [("A", "B"), ("A", "C")])      # 'a' matched case-insensitively
        self.assertEqual(len(b.warnings), 3)                       # duplicate, self-loop, invalid
        self.assertEqual(b.graph["A"], ["B", "C"])

    def test_duplicate_locations_ignored(self):
        b = build_graph(["A", "a", " A ", "B"], [])
        self.assertEqual(list(b.graph), ["A", "B"])

    def test_empty_text_gives_empty_graph(self):
        self.assertEqual(graph_from_text("", "").graph, {})
        self.assertEqual(graph_from_text("  \n ", "\n\n").graph, {})

    def test_text_parsing_formats(self):
        pairs, warnings = parse_connections_text("A - B\nC, D\nE -> F\nG-H\n# comment\nbroken line\nX - \n")
        self.assertEqual(pairs, [("A", "B"), ("C", "D"), ("E", "F"), ("G", "H")])
        self.assertEqual(len(warnings), 2)

    def test_graph_from_text(self):
        b = graph_from_text("A, B\nC", "A - B\nB - C\nC - Z")
        self.assertEqual(b.graph, {"A": ["B"], "B": ["A", "C"], "C": ["B"]})
        self.assertEqual(len(b.warnings), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
