from enum import Enum, auto
from typing import List, Set, Optional, Dict, Tuple
from weakref import WeakValueDictionary


class NodeType(Enum):
    AND = auto()
    OR = auto()
    LITERAL = auto()
    ITE = auto()
    CONSTANT = auto()


class CandidateFunction:
    """
    Represents a Boolean function in Negation Normal Form (NNF) or general DAG if ITE is used.
    Should be instantiated via FunctionManager to ensure structural hashing.
    """

    def __init__(
        self,
        node_type: NodeType,
        children: Optional[List["CandidateFunction"]] = None,
        value: Optional[int] = None,
        repairable: bool = True,
    ):
        self.node_type = node_type
        # Use tuple for immutability and hashing
        self.children: Tuple["CandidateFunction", ...] = (
            tuple(children) if children is not None else ()
        )
        self.value: Optional[int] = value
        self.repairable = repairable
        self.repair_count = 0
        self.id = id(self)
        self.dependencies: Set[int] = set()
        # Caching properties
        self._support: Optional[Set[int]] = None
        self._size: Optional[int] = None
        self._depth: Optional[int] = None
        self._hash: Optional[int] = None

    @property
    def is_true(self) -> bool:
        return self.node_type == NodeType.CONSTANT and self.value == 1

    @property
    def is_false(self) -> bool:
        return self.node_type == NodeType.CONSTANT and self.value == 0

    @property
    def support(self) -> Set[int]:
        if self._support is None:
            if self.node_type == NodeType.LITERAL:
                assert self.value is not None
                self._support = {abs(self.value)}
            elif self.node_type == NodeType.CONSTANT:
                self._support = set()
            else:
                s = set()
                for child in self.children:
                    s.update(child.support)
                self._support = s
        return self._support

    @property
    def size(self) -> int:
        """Returns the size of the subgraph rooted at this node (number of nodes)."""
        if self._size is None:
            if (
                self.node_type == NodeType.LITERAL
                or self.node_type == NodeType.CONSTANT
            ):
                self._size = 1
            else:
                self._size = 1 + sum(child.size for child in self.children)
        return self._size

    @property
    def depth(self) -> int:
        if self._depth is None:
            if (
                self.node_type == NodeType.LITERAL
                or self.node_type == NodeType.CONSTANT
            ):
                self._depth = 0
            else:
                self._depth = 1 + max(
                    (child.depth for child in self.children), default=0
                )
        return self._depth

    def evaluate(self, assignment: Dict[int, bool]) -> bool:
        if self.node_type == NodeType.CONSTANT:
            return bool(self.value)

        if self.node_type == NodeType.LITERAL:
            assert self.value is not None
            var = abs(self.value)
            val = assignment.get(var, False)
            return val if self.value > 0 else not val

        elif self.node_type == NodeType.AND:
            return all(child.evaluate(assignment) for child in self.children)

        elif self.node_type == NodeType.OR:
            return any(child.evaluate(assignment) for child in self.children)

        elif self.node_type == NodeType.ITE:
            # ITE(cond, true_branch, false_branch)
            cond = self.children[0].evaluate(assignment)
            if cond:
                return self.children[1].evaluate(assignment)
            else:
                return self.children[2].evaluate(assignment)

        return False

    def substitute(
        self, manager: "FunctionManager", mapping: Dict[int, "CandidateFunction"]
    ) -> "CandidateFunction":
        """
        Substitutes variables (literals) based on the mapping.
        mapping: dict from variable ID (int) to a new Function.
        """
        if self.node_type == NodeType.CONSTANT:
            return self

        if self.node_type == NodeType.LITERAL:
            assert self.value is not None
            var = abs(self.value)
            if var in mapping:
                replacement = mapping[var]
                if self.value < 0:
                    return replacement.Not(manager)
                return replacement
            return self

        new_children = [child.substitute(manager, mapping) for child in self.children]

        if self.node_type == NodeType.AND:
            return manager.get_and(new_children)
        elif self.node_type == NodeType.OR:
            return manager.get_or(new_children)
        elif self.node_type == NodeType.ITE:
            return manager.get_ite(new_children[0], new_children[1], new_children[2])

        return self

    def Not(self, manager: "FunctionManager") -> "CandidateFunction":
        """
        Returns the negation of this function, maintaining NNF.
        """
        if self.node_type == NodeType.CONSTANT:
            return manager.get_false() if self.value == 1 else manager.get_true()

        if self.node_type == NodeType.LITERAL:
            assert self.value is not None
            return manager.get_lit(-self.value)

        elif self.node_type == NodeType.AND:
            # ~(A & B) = ~A | ~B
            return manager.get_or([child.Not(manager) for child in self.children])

        elif self.node_type == NodeType.OR:
            # ~(A | B) = ~A & ~B
            return manager.get_and([child.Not(manager) for child in self.children])

        elif self.node_type == NodeType.ITE:
            # ~ITE(c, t, e) = ITE(c, ~t, ~e)
            return manager.get_ite(
                self.children[0],
                self.children[1].Not(manager),
                self.children[2].Not(manager),
            )

        return self

    def to_cnf(self, manager: "FunctionManager") -> List[List[int]]:
        """
        Converts to CNF (list of clauses) using Tseitin transformation if necessary?
        Actually, for simple NNF validation or solving, we might just want to use a solver wrapper
        that handles the DAG. But if explicit CNF is needed:
        """
        # Placeholder for full Tseitin implementation.
        # For now, we assume this feature is mainly for interfacing with SAT solvers
        # which usually handle this via API (add_clause).
        # Implementing a full Tseitin transformer returning raw integers requires a fresh variable generator.
        raise NotImplementedError("Full CNF export requires a variable manager.")

    def __repr__(self) -> str:
        if self.node_type == NodeType.CONSTANT:
            return "True" if self.value == 1 else "False"
        if self.node_type == NodeType.LITERAL:
            return str(self.value)
        elif self.node_type == NodeType.AND:
            return f"AND({', '.join(repr(c) for c in self.children)})"
        elif self.node_type == NodeType.OR:
            return f"OR({', '.join(repr(c) for c in self.children)})"
        elif self.node_type == NodeType.ITE:
            return f"ITE({repr(self.children[0])}, {repr(self.children[1])}, {repr(self.children[2])})"
        return "Unknown"

    def __eq__(self, other):
        if not isinstance(other, CandidateFunction):
            return False
        # Structural equality
        return (
            self.node_type == other.node_type
            and self.value == other.value
            and self.children == other.children
        )

    def __hash__(self):
        if self._hash is None:
            # children are already a tuple
            self._hash = hash((self.node_type, self.value, self.children))
        return self._hash


class FunctionManager:
    def __init__(self):
        # Cache: (node_type, value, children_tuple) -> Function
        self._cache: WeakValueDictionary = WeakValueDictionary()
        # Initialize constants
        self.true_node = self._create_constant(1)
        self.false_node = self._create_constant(0)

    def _create_constant(self, value: int) -> CandidateFunction:
        key = (NodeType.CONSTANT, value, ())
        node = CandidateFunction(NodeType.CONSTANT, value=value)
        self._cache[key] = node
        return node

    def get_true(self) -> CandidateFunction:
        return self.true_node

    def get_false(self) -> CandidateFunction:
        return self.false_node

    def _get_from_cache(self, key, creator_func):
        node = self._cache.get(key)
        if node is None:
            node = creator_func()
            self._cache[key] = node
        return node

    def get_lit(self, value: int) -> CandidateFunction:
        key = (NodeType.LITERAL, value, ())
        return self._get_from_cache(
            key, lambda: CandidateFunction(NodeType.LITERAL, value=value)
        )

    def get_and(self, children: List[CandidateFunction]) -> CandidateFunction:
        # Simplification
        flattened = []
        for child in children:
            if child.is_false:
                return self.get_false()
            if child.is_true:
                continue  # 1 & A = A
            if child.node_type == NodeType.AND:
                flattened.extend(child.children)
            else:
                flattened.append(child)

        # Deduplication
        unique_children = sorted(list(set(flattened)), key=lambda x: hash(x))

        # Check for complementary literals x and -x -> False
        seen_literals = {}
        for child in unique_children:
            if child.node_type == NodeType.LITERAL:
                assert child.value is not None
                if -child.value in seen_literals:
                    return self.get_false()
                seen_literals[child.value] = True

        children_tuple = tuple(unique_children)
        key = (NodeType.AND, None, children_tuple)

        if len(unique_children) == 0:
            return self.get_true()

        if len(unique_children) == 1:
            return unique_children[0]

        return self._get_from_cache(
            key, lambda: CandidateFunction(NodeType.AND, children=list(children_tuple))
        )

    def get_or(self, children: List[CandidateFunction]) -> CandidateFunction:
        flattened = []
        for child in children:
            if child.is_true:
                return self.get_true()
            if child.is_false:
                continue  # 0 | A = A
            if child.node_type == NodeType.OR:
                flattened.extend(child.children)
            else:
                flattened.append(child)

        unique_children = sorted(list(set(flattened)), key=lambda x: hash(x))

        # Check for x and -x -> True
        seen_literals = {}
        for child in unique_children:
            if child.node_type == NodeType.LITERAL:
                assert child.value is not None
                if -child.value in seen_literals:
                    return self.get_true()
                seen_literals[child.value] = True

        children_tuple = tuple(unique_children)
        key = (NodeType.OR, None, children_tuple)

        if len(unique_children) == 0:
            return self.get_false()

        if len(unique_children) == 1:
            return unique_children[0]

        return self._get_from_cache(
            key, lambda: CandidateFunction(NodeType.OR, children=list(children_tuple))
        )

    def get_ite(
        self,
        condition: CandidateFunction,
        true_branch: CandidateFunction,
        false_branch: CandidateFunction,
    ) -> CandidateFunction:
        # Simplification
        if condition.is_true:
            return true_branch
        if condition.is_false:
            return false_branch
        if true_branch == false_branch:
            return true_branch
        if true_branch.is_true and false_branch.is_false:
            return condition

        key = (NodeType.ITE, None, (condition, true_branch, false_branch))
        return self._get_from_cache(
            key,
            lambda: CandidateFunction(
                NodeType.ITE, children=[condition, true_branch, false_branch]
            ),
        )
