# SoD Graph Model
# Access modeled as directed graph for transitive conflict detection

"""
Graph Construction for Access Risk Analysis.

Models access relationships as:
(User) ──has_role──> (Role)
(Role) ──grants──> (Privilege / TCODE)
(TCODE) ──affects──> (Business Action)
(Business Action) ──enables──> (Risk Outcome)

A risk path = any path that violates a control principle.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the access graph."""
    USER = "USER"
    ROLE = "ROLE"
    PRIVILEGE = "PRIVILEGE"  # TCODE or authorization object
    ACTION = "ACTION"  # Business action (CREATE_VENDOR, EXECUTE_PAYMENT)
    OUTCOME = "OUTCOME"  # Risk outcome (FRAUD, DATA_BREACH)
    SYSTEM = "SYSTEM"  # SAP system
    ORG_UNIT = "ORG_UNIT"  # Organizational unit


class EdgeType(Enum):
    """Types of edges in the access graph."""
    HAS_ROLE = "HAS_ROLE"
    GRANTS = "GRANTS"
    ENABLES = "ENABLES"
    LEADS_TO = "LEADS_TO"
    BELONGS_TO = "BELONGS_TO"
    CONTAINS = "CONTAINS"


@dataclass
class GraphNode:
    """Node in the access graph."""
    node_id: str
    node_type: NodeType
    label: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    system_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "attributes": self.attributes,
            "system_id": self.system_id,
        }


@dataclass
class GraphEdge:
    """Edge in the access graph."""
    source: str
    target: str
    edge_type: EdgeType
    attributes: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "attributes": self.attributes,
            "weight": self.weight,
        }


class SoDGraph:
    """
    Directed graph for SoD analysis.

    Enables detection of:
    - Indirect SoD violations
    - Multi-role escalation paths
    - "Harmless alone, dangerous together" access
    - Control bypass chains

    Can use NetworkX if available, otherwise uses pure Python implementation.
    """

    def __init__(self):
        """Initialize the SoD graph."""
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, Set[str]] = {}  # node_id -> set of target node_ids
        self._reverse_adjacency: Dict[str, Set[str]] = {}  # node_id -> set of source node_ids

        # Try to use NetworkX for better performance
        self._nx_graph = None
        try:
            import networkx as nx
            self._nx_graph = nx.DiGraph()
            self._use_networkx = True
        except ImportError:
            self._use_networkx = False
            logger.info("NetworkX not available, using pure Python graph implementation")

    # Node operations

    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        label: Optional[str] = None,
        **attributes
    ) -> GraphNode:
        """Add a node to the graph."""
        node = GraphNode(
            node_id=node_id,
            node_type=node_type,
            label=label or node_id,
            attributes=attributes
        )
        self._nodes[node_id] = node

        if node_id not in self._adjacency:
            self._adjacency[node_id] = set()
        if node_id not in self._reverse_adjacency:
            self._reverse_adjacency[node_id] = set()

        if self._use_networkx:
            self._nx_graph.add_node(
                node_id,
                type=node_type.value,
                label=label or node_id,
                **attributes
            )

        return node

    def add_user(self, user_id: str, **attributes) -> GraphNode:
        """Add a user node."""
        return self.add_node(user_id, NodeType.USER, user_id, **attributes)

    def add_role(self, role_id: str, description: str = "", **attributes) -> GraphNode:
        """Add a role node."""
        return self.add_node(role_id, NodeType.ROLE, role_id, description=description, **attributes)

    def add_privilege(self, priv_id: str, tcode: str = "", **attributes) -> GraphNode:
        """Add a privilege/tcode node."""
        return self.add_node(priv_id, NodeType.PRIVILEGE, priv_id, tcode=tcode, **attributes)

    def add_action(self, action_id: str, description: str = "", **attributes) -> GraphNode:
        """Add a business action node."""
        return self.add_node(action_id, NodeType.ACTION, action_id, description=description, **attributes)

    def add_outcome(self, outcome_id: str, description: str = "", **attributes) -> GraphNode:
        """Add a risk outcome node."""
        return self.add_node(outcome_id, NodeType.OUTCOME, outcome_id, description=description, **attributes)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    # Edge operations

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        **attributes
    ) -> GraphEdge:
        """Add an edge to the graph."""
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            attributes=attributes
        )
        self._edges.append(edge)

        if source not in self._adjacency:
            self._adjacency[source] = set()
        self._adjacency[source].add(target)

        if target not in self._reverse_adjacency:
            self._reverse_adjacency[target] = set()
        self._reverse_adjacency[target].add(source)

        if self._use_networkx:
            self._nx_graph.add_edge(
                source, target,
                rel=edge_type.value,
                weight=weight,
                **attributes
            )

        return edge

    def link_user_role(self, user_id: str, role_id: str, **attributes) -> GraphEdge:
        """Link user to role."""
        return self.add_edge(user_id, role_id, EdgeType.HAS_ROLE, **attributes)

    def link_role_privilege(self, role_id: str, priv_id: str, **attributes) -> GraphEdge:
        """Link role to privilege."""
        return self.add_edge(role_id, priv_id, EdgeType.GRANTS, **attributes)

    def link_privilege_action(self, priv_id: str, action_id: str, **attributes) -> GraphEdge:
        """Link privilege to business action."""
        return self.add_edge(priv_id, action_id, EdgeType.ENABLES, **attributes)

    def link_action_outcome(self, action_id: str, outcome_id: str, **attributes) -> GraphEdge:
        """Link action to risk outcome."""
        return self.add_edge(action_id, outcome_id, EdgeType.LEADS_TO, **attributes)

    # Graph traversal

    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all nodes reachable from a given node (BFS)."""
        if self._use_networkx:
            import networkx as nx
            return set(nx.descendants(self._nx_graph, node_id))

        # Pure Python BFS
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited

    def get_ancestors(self, node_id: str) -> Set[str]:
        """Get all nodes that can reach a given node."""
        if self._use_networkx:
            import networkx as nx
            return set(nx.ancestors(self._nx_graph, node_id))

        # Pure Python reverse BFS
        visited = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            for neighbor in self._reverse_adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return visited

    def get_reachable_by_type(self, node_id: str, target_type: NodeType) -> Set[str]:
        """Get all reachable nodes of a specific type."""
        descendants = self.get_descendants(node_id)
        return {
            n for n in descendants
            if self._nodes.get(n) and self._nodes[n].node_type == target_type
        }

    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two nodes (BFS)."""
        if self._use_networkx:
            import networkx as nx
            try:
                return nx.shortest_path(self._nx_graph, source, target)
            except nx.NetworkXNoPath:
                return None

        # Pure Python BFS for shortest path
        if source == target:
            return [source]

        visited = {source}
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def find_all_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 10
    ) -> List[List[str]]:
        """Find all paths between two nodes (up to max depth)."""
        if self._use_networkx:
            import networkx as nx
            try:
                return list(nx.all_simple_paths(
                    self._nx_graph, source, target, cutoff=max_depth
                ))
            except nx.NetworkXNoPath:
                return []

        # Pure Python DFS for all paths
        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_depth:
                return
            if current == target:
                paths.append(path.copy())
                return

            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(source, [source], {source})
        return paths

    # User-centric operations

    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles for a user."""
        roles = set()
        for neighbor in self._adjacency.get(user_id, set()):
            node = self._nodes.get(neighbor)
            if node and node.node_type == NodeType.ROLE:
                roles.add(neighbor)
        return roles

    def get_user_privileges(self, user_id: str) -> Set[str]:
        """Get all privileges reachable by a user."""
        return self.get_reachable_by_type(user_id, NodeType.PRIVILEGE)

    def get_user_actions(self, user_id: str) -> Set[str]:
        """Get all business actions reachable by a user."""
        return self.get_reachable_by_type(user_id, NodeType.ACTION)

    def get_user_outcomes(self, user_id: str) -> Set[str]:
        """Get all risk outcomes reachable by a user."""
        return self.get_reachable_by_type(user_id, NodeType.OUTCOME)

    # Role-centric operations

    def get_role_privileges(self, role_id: str) -> Set[str]:
        """Get all privileges granted by a role."""
        return self.get_reachable_by_type(role_id, NodeType.PRIVILEGE)

    def get_role_actions(self, role_id: str) -> Set[str]:
        """Get all business actions enabled by a role."""
        return self.get_reachable_by_type(role_id, NodeType.ACTION)

    def get_role_users(self, role_id: str) -> Set[str]:
        """Get all users with a role."""
        users = set()
        for source in self._reverse_adjacency.get(role_id, set()):
            node = self._nodes.get(source)
            if node and node.node_type == NodeType.USER:
                users.add(source)
        return users

    # Graph statistics

    def node_count(self) -> int:
        """Get total number of nodes."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Get total number of edges."""
        return len(self._edges)

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        type_counts = {}
        for node in self._nodes.values():
            type_name = node.node_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": type_counts,
            "using_networkx": self._use_networkx,
        }

    # Serialization

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "statistics": self.get_statistics(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoDGraph":
        """Deserialize graph from dictionary."""
        graph = cls()

        for node_data in data.get("nodes", []):
            graph.add_node(
                node_id=node_data["node_id"],
                node_type=NodeType(node_data["node_type"]),
                label=node_data.get("label"),
                **node_data.get("attributes", {})
            )

        for edge_data in data.get("edges", []):
            graph.add_edge(
                source=edge_data["source"],
                target=edge_data["target"],
                edge_type=EdgeType(edge_data["edge_type"]),
                weight=edge_data.get("weight", 1.0),
                **edge_data.get("attributes", {})
            )

        return graph

    # Bulk loading

    def load_from_sap_data(
        self,
        user_roles: Dict[str, List[str]],
        role_tcodes: Dict[str, List[str]],
        tcode_actions: Dict[str, List[str]]
    ):
        """
        Bulk load graph from SAP data.

        Args:
            user_roles: user_id -> list of role names
            role_tcodes: role_name -> list of tcodes
            tcode_actions: tcode -> list of business actions
        """
        # Add users and their roles
        for user_id, roles in user_roles.items():
            if user_id not in self._nodes:
                self.add_user(user_id)
            for role in roles:
                if role not in self._nodes:
                    self.add_role(role)
                self.link_user_role(user_id, role)

        # Add roles and their tcodes
        for role, tcodes in role_tcodes.items():
            if role not in self._nodes:
                self.add_role(role)
            for tcode in tcodes:
                if tcode not in self._nodes:
                    self.add_privilege(tcode, tcode=tcode)
                self.link_role_privilege(role, tcode)

        # Add tcodes and their actions
        for tcode, actions in tcode_actions.items():
            if tcode not in self._nodes:
                self.add_privilege(tcode, tcode=tcode)
            for action in actions:
                if action not in self._nodes:
                    self.add_action(action)
                self.link_privilege_action(tcode, action)

        logger.info(f"Loaded graph: {self.get_statistics()}")
