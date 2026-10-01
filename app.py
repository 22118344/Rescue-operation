"""
app.py - Streamlit user interface for the Depth-Limited Search rescue project.

Run with:   streamlit run app.py

This file only collects input and displays output.
All search logic lives in dls.py; graph building lives in graph_data.py.
"""

import streamlit as st

from dls import (CUTOFF, EXPAND, FOUND, GOAL, INVALID_INPUT, LIMIT, NOT_FOUND, SKIP,
                 depth_limited_search, format_path)
from graph_data import (DEFAULT_CONNECTIONS, DEFAULT_DEPTH, DEFAULT_LOCATIONS, DEFAULT_START,
                        DEFAULT_TARGET, connections_to_text, default_graph, graph_from_text,
                        locations_to_text)

st.set_page_config(page_title="Rescue Search - Depth-Limited Search", page_icon="🧭", layout="wide")

DEFAULT_MODE = "Default rescue map"
CUSTOM_MODE = "Custom graph"

ACTION_LABEL = {
    EXPAND: "Explore neighbours",
    GOAL: "🎯 Target found",
    LIMIT: "⛔ Depth limit reached",
    SKIP: "↩ Already explored",
}
STATUS_LABEL = {FOUND: "FOUND", CUTOFF: "CUTOFF", NOT_FOUND: "NOT FOUND", INVALID_INPUT: "INVALID INPUT"}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    """Give every widget / stored value a starting value (only once)."""
    defaults = {
        "run": None,                       # last search that was executed
        "run_id": 0,
        "graph_mode": DEFAULT_MODE,
        "loc_text": locations_to_text(DEFAULT_LOCATIONS),
        "edge_text": connections_to_text(DEFAULT_CONNECTIONS),
        "start": DEFAULT_START,
        "target": DEFAULT_TARGET,
        "depth": DEFAULT_DEPTH,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all():
    """Callback of the Reset button: back to the default map and default settings."""
    st.session_state["run"] = None
    st.session_state["graph_mode"] = DEFAULT_MODE
    st.session_state["loc_text"] = locations_to_text(DEFAULT_LOCATIONS)
    st.session_state["edge_text"] = connections_to_text(DEFAULT_CONNECTIONS)
    st.session_state["start"] = DEFAULT_START
    st.session_state["target"] = DEFAULT_TARGET
    st.session_state["depth"] = DEFAULT_DEPTH


def signature(graph, start, target, depth):
    """A comparable snapshot of the current settings (to detect out-of-date results)."""
    return (tuple((k, tuple(v)) for k, v in graph.items()), start, target, int(depth))


# ---------------------------------------------------------------------------
# Graph drawing (Graphviz DOT text -> st.graphviz_chart, no extra library needed)
# ---------------------------------------------------------------------------
def dot_escape(text):
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def tree_edges_from_steps(steps):
    """Connections the search actually walked along (parent -> child)."""
    return [(s.parent, s.node) for s in steps if s.parent is not None and s.action != SKIP]


def build_dot(graph, start, target, explored=None, path=None, skipped=None,
              current=None, tree_edges=None, target_found=False):
    """
    Build a Graphviz DOT description of the map.
      explored : {node: depth} nodes the search explored
      path     : final path (highlighted)
      skipped  : nodes not explored because of the depth limit (dashed)
      current  : node being examined in a replayed step (orange border)
    """
    explored = explored or {}
    path = path or []
    skipped = set(skipped or [])
    tree_edges = {frozenset(e) for e in (tree_edges or [])}
    path_nodes = set(path)
    path_edges = {frozenset(pair) for pair in zip(path, path[1:])}

    out = [
        "graph G {",
        "  graph [nodesep=0.45, ranksep=0.7];",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, '
        'fillcolor="#ffffff", fontcolor="#111111", color="#607d8b"];',
        '  edge [color="#90a4ae"];',
    ]

    for node in graph:
        label = dot_escape(node)
        attrs = {}
        if node in explored:
            label += f"\\n(depth {explored[node]})"
            attrs["fillcolor"] = "#bbdefb"
        elif node in skipped:
            label += "\\n(beyond limit)"
            attrs["style"] = "rounded,filled,dashed"
            attrs["fillcolor"] = "#eeeeee"
        if node in path_nodes:
            attrs["fillcolor"] = "#ffe082"
        if node == start:
            attrs["fillcolor"] = "#66bb6a"
            label += "\\nSTART"
        if node == target:
            if node == start:
                label += " = TARGET"
            elif target_found:
                attrs["fillcolor"] = "#ef5350"
                attrs["fontcolor"] = "#ffffff"
                label += "\\nTARGET FOUND"
            else:
                attrs["fillcolor"] = "#ffcdd2"
                attrs["color"] = "#c62828"
                attrs["penwidth"] = "2"
                label += "\\nTARGET"
        if node == current:
            attrs["color"] = "#ff6f00"
            attrs["penwidth"] = "3.5"
        extra = "".join(f', {k}="{v}"' for k, v in attrs.items())
        out.append(f'  "{dot_escape(node)}" [label="{label}"{extra}];')

    seen = set()
    for a, neighbours in graph.items():
        for b in neighbours:
            key = frozenset((a, b))
            if a == b or key in seen:
                continue
            seen.add(key)
            if key in path_edges:
                style = ' [color="#e65100", penwidth=3.5]'
            elif key in tree_edges:
                style = ' [color="#1976d2", penwidth=2]'
            else:
                style = ""
            out.append(f'  "{dot_escape(a)}" -- "{dot_escape(b)}"{style};')
    out.append("}")
    return "\n".join(out)


def show_legend():
    st.caption("🟩 start  ·  🟥 target found  ·  🟧 final path  ·  🟦 explored (with its depth)  ·  "
               "⬜ dashed = not explored because of the depth limit  ·  blue line = connection walked by the search")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    """Draw the sidebar and return (graph_build, start, target, depth, search_clicked)."""
    with st.sidebar:
        st.header("⚙️ Controls")
        st.selectbox("Search algorithm", ["Depth-Limited Search (DLS)"], disabled=True)
        st.radio("Graph source", [DEFAULT_MODE, CUSTOM_MODE], key="graph_mode")

        if st.session_state["graph_mode"] == CUSTOM_MODE:
            with st.expander("Edit custom graph", expanded=True):
                st.text_area("Locations (one per line or comma-separated)", key="loc_text", height=150)
                st.text_area("Connections (one per line, e.g. Village - School)", key="edge_text", height=200)
            build = graph_from_text(st.session_state["loc_text"], st.session_state["edge_text"])
        else:
            build = default_graph()

        nodes = list(build.graph)
        clicked = False
        start = target = None
        depth = st.session_state["depth"]

        if nodes:
            # Keep stored choices valid if the graph changed.
            if st.session_state.get("start") not in nodes:
                st.session_state["start"] = nodes[0]
            if st.session_state.get("target") not in nodes:
                st.session_state["target"] = nodes[-1]
            start = st.selectbox("Starting location", nodes, key="start")
            target = st.selectbox("Target location (missing person)", nodes, key="target")
            depth = st.number_input("Maximum search depth", min_value=0, max_value=20, step=1, key="depth")
            clicked = st.button("🔍 Search", type="primary")
        else:
            st.warning("The graph is empty. Add locations to continue.")
        st.button("↺ Reset", on_click=reset_all)
    return build, start, target, int(depth), clicked


# ---------------------------------------------------------------------------
# Main-page sections
# ---------------------------------------------------------------------------
def show_graph_section(build, start, target, run, up_to_date):
    st.subheader("🗺️ Graph visualization")
    if run and run["result"].status != INVALID_INPUT:
        r = run["result"]
        dot = build_dot(run["graph"], r.start, r.target, explored=r.depth_of, path=r.path,
                        skipped=r.skipped_by_limit, tree_edges=tree_edges_from_steps(r.steps),
                        target_found=r.found)
        if not up_to_date:
            st.info("The controls changed after the last search. Press **Search** to update this picture.")
    else:
        dot = build_dot(build.graph, start, target)
        st.caption("Preview of the map. Press **Search** in the sidebar to run DLS.")
    st.graphviz_chart(dot)
    show_legend()


def show_config(build, start, target, depth):
    st.subheader("🧩 Search configuration")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Algorithm", "DLS")
    c2.metric("Starting location", start)
    c3.metric("Target location", target)
    c4.metric("Depth limit", depth)
    with st.expander("Show the graph as an adjacency list"):
        st.dataframe([{"Location": n, "Connected to": ", ".join(nb) if nb else "(no connections)"}
                      for n, nb in build.graph.items()], hide_index=True)


def show_execution(run):
    st.subheader("▶️ Search execution")
    if not run:
        st.info("No search has been run yet. Choose the settings in the sidebar and press **Search**.")
        return
    r = run["result"]
    if r.status == INVALID_INPUT:
        st.error("The search could not start because of invalid input.")
        return
    st.write(f"DLS started at **{r.start}** (depth 0) and explored the map depth-first, "
             f"never going deeper than **{r.depth_limit}**. It made **{len(r.steps)}** recorded steps "
             f"and explored **{r.nodes_explored}** distinct location(s).")


def show_result(run):
    st.subheader("📋 Search result")
    if not run:
        st.info("The result will appear here after you press **Search**.")
        return
    r = run["result"]
    if r.status == FOUND:
        st.success("🎯 TARGET FOUND")
    elif r.status == CUTOFF:
        st.warning("⚠️ TARGET NOT FOUND WITHIN DEPTH LIMIT  (CUTOFF)")
    elif r.status == NOT_FOUND:
        st.error("❌ TARGET NOT FOUND  (UNREACHABLE)")
    else:
        st.error(f"Invalid input: {r.reason}")
        return

    left, right = st.columns(2)
    left.markdown(f"**Target:** {r.target}  \n**Starting location:** {r.start}  \n"
                  f"**Search depth limit:** {r.depth_limit}")
    right.markdown(f"**Nodes explored:** {r.nodes_explored}")
    if r.found:
        right.markdown(f"**Depth where found:** {r.path_length}  \n**Path:** {format_path(r.path)}")
    st.markdown(f"**Reason:** {r.reason}")


def show_path(run):
    st.subheader("🛣️ Search path")
    if not run or run["result"].status == INVALID_INPUT:
        st.info("The path will appear here after a successful search.")
        return
    r = run["result"]
    if r.found:
        st.markdown(f"### {format_path(r.path)}")
        st.dataframe([{"Hop": i, "Location": name, "Depth": i} for i, name in enumerate(r.path)],
                     hide_index=True)
        st.caption("DLS returns the first route it finds while going depth-first. "
                   "That route is not guaranteed to be the shortest one.")
    else:
        st.info("No path: the target was not reached.")


def show_stats(run):
    st.subheader("📊 Search statistics")
    if not run or run["result"].status == INVALID_INPUT:
        st.info("Statistics will appear here after a search.")
        return
    r = run["result"]
    row1 = st.columns(4)
    row1[0].metric("Total locations", len(run["graph"]))
    row1[1].metric("Total connections", run["edge_count"])
    row1[2].metric("Search depth limit", r.depth_limit)
    row1[3].metric("Search result", STATUS_LABEL[r.status])
    row2 = st.columns(4)
    row2[0].metric("Nodes visited", r.nodes_explored)
    row2[1].metric("Maximum depth reached", r.max_depth_reached)
    row2[2].metric("Path length (connections)", r.path_length if r.found else "-")
    row2[3].metric("Nodes skipped (depth limit)", len(r.skipped_by_limit))


def show_steps(run):
    st.subheader("👣 Step-by-step exploration")
    if not run or run["result"].status == INVALID_INPUT:
        st.info("The exploration log will appear here after a search.")
        return
    r = run["result"]

    st.markdown("**Locations explored, grouped by depth**")
    levels = {}
    for node, depth in r.depth_of.items():
        levels.setdefault(depth, []).append(node)
    for depth in sorted(levels):
        st.markdown(f"- **Depth {depth}:** {', '.join(levels[depth])}")
    if r.skipped_by_limit:
        st.markdown(f"- **Skipped because of the depth limit ({r.depth_limit}):** {', '.join(r.skipped_by_limit)}")
    else:
        st.markdown("- **Skipped because of the depth limit:** none")

    st.markdown("**Exploration log** (depth-first order, one row per step)")
    st.dataframe(
        [{"Step": s.number, "Current node": s.node, "Depth": s.depth, "Parent": s.parent or "-",
          "Action": ACTION_LABEL[s.action], "Details": s.detail} for s in r.steps],
        hide_index=True)

    st.markdown("**Replay**: drag the slider to see the map after each step")
    total = len(r.steps)
    step_no = st.slider("Show the map after step", 0, total, total, key=f"replay_{run['id']}")
    if step_no == total:
        dot = build_dot(run["graph"], r.start, r.target, explored=r.depth_of, path=r.path,
                        skipped=r.skipped_by_limit, tree_edges=tree_edges_from_steps(r.steps),
                        target_found=r.found)
    else:
        explored = {}
        for s in r.steps[:step_no]:
            if s.action != SKIP:
                explored[s.node] = min(explored.get(s.node, s.depth), s.depth)
        current = r.steps[step_no - 1].node if step_no > 0 else None
        dot = build_dot(run["graph"], r.start, r.target, explored=explored, current=current,
                        tree_edges=tree_edges_from_steps(r.steps[:step_no]))
    if step_no > 0:
        s = r.steps[step_no - 1]
        st.caption(f"Step {s.number}: **{s.node}** at depth {s.depth} - {s.detail}")
    st.graphviz_chart(dot)


# ---------------------------------------------------------------------------
# Learning section
# ---------------------------------------------------------------------------
def show_learning():
    st.divider()
    st.header("📚 Learn: how Depth-Limited Search works")
    tab_concepts, tab_example, tab_compare = st.tabs(["Key ideas", "Worked example", "BFS vs DFS vs DLS"])

    with tab_concepts:
        st.markdown("""
**What is a graph?** A set of places (nodes) together with the connections (edges) between them.
A road map is a graph.

**What is a node?** One place in the graph, for example *Village* or *Hospital*.

**What is an edge?** A direct connection between two nodes, for example the road *Village - School*.

**What is search depth?** The number of connections between the starting location and a place.
The start has depth 0, its direct neighbours have depth 1, their neighbours depth 2, and so on.

**What is Depth-First Search (DFS)?** A search that follows one route as deep as it can go, and only
then backs up and tries the next route. On its own it has no limit, so on a very deep or endless
map it can wander far from the start.

**What is Depth-Limited Search (DLS)?** DFS with a maximum depth *L*. A place at depth *L* is still
checked (it might be the target) but the search does not go past it.

**Why is DLS suitable for the rescue problem?** The team can only search a limited number of levels from
the starting point. The depth limit models exactly that: places further away than *L* are never searched.

**What happens when the limit is reached?** The search stops going deeper along that route and backs up
to try other routes. If the target was not found and some places were left unexplored, the answer is
**CUTOFF**: "not found *within the limit*", which is not the same as "does not exist".
""")

    with tab_example:
        st.markdown("Chain of four places: **A - B - C - D**. Start = A, Target = D. "
                    "This example is executed by the real `depth_limited_search` function.")
        chain = {"A": ["B"], "B": ["A", "C"], "C": ["B", "D"], "D": ["C"]}
        for limit in (2, 3):
            res = depth_limited_search(chain, "A", "D", limit)
            st.markdown(f"**Depth limit = {limit}** → result: **{STATUS_LABEL[res.status]}**")
            st.dataframe([{"Step": s.number, "Node": s.node, "Depth": s.depth,
                           "Action": ACTION_LABEL[s.action], "Details": s.detail} for s in res.steps],
                         hide_index=True)
        st.markdown("With limit 2, D is at depth 3, so it is never searched and the result is "
                    "CUTOFF / TARGET NOT FOUND WITHIN DEPTH LIMIT. With limit 3 the target is found.")

    with tab_compare:
        st.table([
            {"Property": "Search strategy", "BFS": "Level by level (shallowest first)",
             "DFS": "One branch as deep as possible, then back up",
             "DLS": "DFS that never goes deeper than the limit L"},
            {"Property": "Data structure", "BFS": "Queue", "DFS": "Stack / recursion", "DLS": "Stack / recursion"},
            {"Property": "Memory requirement", "BFS": "High: O(b^d)", "DFS": "Low: O(b·m)",
             "DLS": "Low: O(b·L)"},
            {"Property": "Depth restriction", "BFS": "None", "DFS": "None", "DLS": "Yes, maximum depth L"},
            {"Property": "Completeness", "BFS": "Yes (finite graph)",
             "DFS": "Only with a cycle check on a finite graph; not on infinite graphs",
             "DLS": "Only if the target is within depth L"},
            {"Property": "Shortest path guaranteed", "BFS": "Yes (equal edge costs)", "DFS": "No", "DLS": "No"},
            {"Property": "Typical use case", "BFS": "Shortest route, nearest target",
             "DFS": "Exploring everything, puzzles, deep search", "DLS": "Search with a fixed budget or range"},
        ])
        st.caption("b = branching factor, d = depth of the shallowest target, m = maximum depth of the graph.")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main():
    init_state()
    build, start, target, depth, clicked = render_sidebar()

    if clicked:
        result = depth_limited_search(build.graph, start, target, depth)   # <- the real DLS run
        st.session_state["run_id"] += 1
        st.session_state["run"] = {
            "id": st.session_state["run_id"],
            "graph": {k: list(v) for k, v in build.graph.items()},
            "edge_count": len(build.edges),
            "result": result,
            "signature": signature(build.graph, start, target, depth),
        }
    run = st.session_state["run"]

    st.title("🧭 Rescue Team Search: Depth-Limited Search")
    st.markdown(
        "A rescue team is looking for a missing person in an area made of connected locations. "
        "Because resources are limited, the team can only search up to a chosen number of levels "
        "from the starting location. This app runs **Depth-Limited Search (DLS)**, a classical "
        "uninformed search algorithm, on that map. It is a search algorithm, not a machine-learning model.")

    if build.warnings:
        with st.expander(f"⚠️ {len(build.warnings)} input warning(s) - some entries were ignored",
                         expanded=st.session_state["graph_mode"] == CUSTOM_MODE):
            for warning in build.warnings:
                st.write("• " + warning)

    if not build.graph:
        st.warning("There is no graph to search yet. In the sidebar, choose the default map or "
                   "enter at least one location in the custom graph.")
        show_learning()
        return

    up_to_date = bool(run) and run["signature"] == signature(build.graph, start, target, depth)

    show_graph_section(build, start, target, run, up_to_date)
    show_config(build, start, target, depth)
    show_execution(run)
    show_result(run)
    show_path(run)
    show_stats(run)
    show_steps(run)
    show_learning()


main()
