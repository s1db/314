from typing import Union, List, Tuple
from pathlib import Path
from src.instance import Instance
from src.dependency_schemes.trivial import TrivialDependencyScheme


class QBFParser:
    @staticmethod
    def from_file(
        path: Union[str, Path], dependency_scheme_class=TrivialDependencyScheme
    ) -> Instance:
        with open(path, "r") as f:
            content = f.read()
        return QBFParser.from_qdimacs(content, dependency_scheme_class)

    @staticmethod
    def from_qdimacs(
        content: str, dependency_scheme_class=TrivialDependencyScheme
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
                    quantifiers[-1] = (q_type, quantifiers[-1][1] + vars)
                else:
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

        quantified_vars_set = {v for _, q_vars in quantifiers for v in q_vars}

        all_vars = set(range(1, num_vars + 1))
        for clause in clauses:
            for lit in clause:
                all_vars.add(abs(lit))

        unquantified_vars = sorted(list(all_vars - quantified_vars_set))

        # Add unquantified variables to the outermost existential block
        if unquantified_vars:
            if not quantifiers:
                quantifiers.append(("e", unquantified_vars))
            elif quantifiers[0][0] == "e":
                # Prepend unquantified variables to the outermost existential block
                quantifiers[0] = ("e", unquantified_vars + quantifiers[0][1])
            else:
                # Add a new outermost existential block
                quantifiers.insert(0, ("e", unquantified_vars))

        return Instance(
            num_vars, num_clauses, quantifiers, clauses, dependency_scheme_class
        )
