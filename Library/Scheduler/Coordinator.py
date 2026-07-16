from __future__ import annotations

import networkx as nx
from croniter import croniter
from datetime import datetime, timedelta
from typing import Union, TYPE_CHECKING

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
    def fits(workflow: Union[str, None], task: Union[str, None], *, samples: int = 6) -> bool:
        if not workflow or not task: return True
        cron = croniter(workflow, datetime.now())
        start = cron.get_next(datetime)
        for _ in range(samples):
            end = cron.get_next(datetime)
            if croniter(task, start - timedelta(seconds=1)).get_next(datetime) >= end: return False
            start = end
        return True

    @staticmethod
    def _clear_(status: Union[str, None], waits: bool, tolerates: bool) -> bool:
        if not tolerates and status == RunStatus.Failure.name: return False
        if waits and not tolerates: return status == RunStatus.Success.name
        if waits: return status in (RunStatus.Success.name, RunStatus.Failure.name)
        return True

    @staticmethod
    def eligible(nodes: list, edges: list, status: dict, *, waits: Union[dict, None] = None, tolerates: Union[dict, None] = None) -> list:
        graph = CoordinatorAPI.graph(nodes, edges)
        waits, tolerates = waits or {}, tolerates or {}
        return [node for node in nodes if status.get(node) is None and all(CoordinatorAPI._clear_(status.get(predecessor), waits.get(node, True), tolerates.get(node, True)) for predecessor in graph.predecessors(node))]

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