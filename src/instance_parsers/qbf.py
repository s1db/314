from typing import Union, List, Tuple
from pathlib import Path
from src.instance import Instance
from src.dependency_schemes.trivial_inter_block import TrivialInterBlockDependencyScheme


class QBFParser:
    @staticmethod
    def from_file(
        path: Union[str, Path],
        dependency_scheme_class=TrivialInterBlockDependencyScheme,
    ) -> Instance:
        with open(path, "r") as f:
            content = f.read()
        return QBFParser.from_qdimacs(content, dependency_scheme_class)

    @staticmethod
    def from_qdimacs(
        content: str, dependency_scheme_class=TrivialInterBlockDependencyScheme
    ) -> Instance:
        lines = content.splitlines()

        # Generator to yield tokens (numbers and keywords)
        def token_generator(lines):
            for line in lines:
                line = line.strip()
                if not line or line.startswith("c"):
                    continue
                # Split by whitespace, but handle the case where multiple spaces exist
                for part in line.split():
                    yield part

        tokens = token_generator(lines)

        num_vars = 0
        num_clauses = 0
        quantifiers: List[Tuple[str, List[int]]] = []
        clauses: List[List[int]] = []

        header_parsed = False

        # State tracking
        current_clause: List[int] = []

        for token in tokens:
            if not header_parsed:
                if token == "p":
                    try:
                        fmt = next(tokens)
                        num_vars = int(next(tokens))
                        num_clauses = int(next(tokens))
                        if fmt != "cnf":
                            raise ValueError(f"Expected 'cnf', got '{fmt}'")
                        header_parsed = True
                    except StopIteration:
                        raise ValueError("Incomplete problem line")
                else:
                    raise ValueError(f"Expected 'p' or comment, got '{token}'")
                continue

            # Parsing prefix or matrix
            if token in ("e", "a"):
                if current_clause:
                    raise ValueError("Quantifier found inside matrix parsing")

                q_type = token
                vars = []

                for v_token in tokens:
                    val = int(v_token)
                    if val == 0:
                        break
                    vars.append(val)

                if quantifiers and quantifiers[-1][0] == q_type:
                    # Merge with existing block
                    quantifiers[-1][1].extend(vars)
                else:
                    # New block
                    quantifiers.append((q_type, vars))

            else:
                lit = int(token)
                if lit == 0:
                    clauses.append(current_clause)
                    current_clause = []
                else:
                    current_clause.append(lit)

        if not header_parsed:
            raise ValueError("No problem line found")

        return Instance(
            num_vars, num_clauses, quantifiers, clauses, dependency_scheme_class
        )
