from __future__ import annotations

from typing import Union, TYPE_CHECKING

import networkx as nx

from Library.Scheduler.Run import RunStatus
from Library.Scheduler.Dependency import DependencyAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class CoordinatorAPI:

    @staticmethod
    def graph(nodes: list, edges: list) -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph

    @staticmethod
    def acyclic(nodes: list, edges: list) -> bool:
        return nx.is_directed_acyclic_graph(CoordinatorAPI.graph(nodes, edges))

    @staticmethod
    def eligible(nodes: list, edges: list, status: dict) -> list:
        graph = CoordinatorAPI.graph(nodes, edges)
        return [node for node in nodes if status.get(node) is None and all(status.get(predecessor) == RunStatus.Success.name for predecessor in graph.predecessors(node))]

    @staticmethod
    def edges(db: DatabaseAPI, wid: str) -> list:
        frame = db.select(schema=DependencyAPI.Schema, table=DependencyAPI.Table, condition='"WID" = :wid:', parameters={"wid": wid}, legacy=False)
        return [(row["Predecessor"], row["Successor"]) for row in frame.to_dicts()]

    @staticmethod
    def link(db: DatabaseAPI, wid: str, predecessor: str, successor: str, by: str = "Scheduler") -> Union[DependencyAPI, None]:
        edges = CoordinatorAPI.edges(db, wid) + [(predecessor, successor)]
        nodes = list({node for edge in edges for node in edge})
        if not CoordinatorAPI.acyclic(nodes, edges): return None
        dependency = DependencyAPI(WID=wid, Predecessor=predecessor, Successor=successor, db=db)
        dependency.save(by=by)
        return dependency