import logging
from typing import Dict, List, Tuple
from pathlib import Path
from src.instance import Instance
from src.candidate_function import CandidateFunction, NodeType

logger = logging.getLogger(__name__)


def write_aiger_skolem(
    path: Path,
    instance: Instance,
    candidates: Dict[int, CandidateFunction],
    include_result_output: bool = False,
):
    """
    Writes the Skolem functions to an ASCII AIGER file (.aag).

    Adheres to the format expected by checkers/caqe_certcheck (and CAQE in general):
    1. AIGER format guidelines: http://fmv.jku.at/aiger/
    2. Input (and Output) variables map to QDIMACS universals (and existentials, respectively).
    3. Symbol table matches QDIMACS variable IDs.

    If include_result_output is True:
    4. One extra output at the end for the "result" check (constant 1 for Skolem, 0 for Herbrand).
    """

    inputs: List[int] = instance.get_universal_vars()
    outputs: List[int] = instance.get_existential_vars()

    aiger_var_counter = 0

    def new_aiger_var():
        nonlocal aiger_var_counter
        aiger_var_counter += 1
        return aiger_var_counter

    # Map candidate nodes (by id) to AIGER literals
    node_to_lit: Dict[int, int] = {}

    # Store AIGER AND gate definitions: (lhs_lit, rhs1_lit, rhs2_lit)
    # resulting in lhs = rhs1 & rhs2
    and_gates: List[Tuple[int, int, int]] = []

    # Set to track visiting variables for cycle detection
    visiting = set()

    # Map QDIMACS Universals to AIGER literals
    # We'll assign them the first I variables
    qdimacs_to_aiger_lit: Dict[int, int] = {}

    for u_var in inputs:
        idx = new_aiger_var()
        # Positive literal is 2*idx
        qdimacs_to_aiger_lit[u_var] = 2 * idx

    # Create constant 0 and 1 gates to avoid using '0' and '1' literals directly
    # as certcheck forbids constant outputs.
    const_zero_var = new_aiger_var()
    const_zero_lit = 2 * const_zero_var
    # Gate: var = 0 & 0
    const_zero_gate = (const_zero_lit, 0, 0)
    and_gates.append(const_zero_gate)

    const_one_var = new_aiger_var()
    const_one_lit = 2 * const_one_var
    # Gate: var = 1 & 1
    const_one_gate = (const_one_lit, 1, 1)
    and_gates.append(const_one_gate)

    def get_const_lit(val: int) -> int:
        return const_one_lit if val else const_zero_lit

    # Recursive function to compile a candidate node to AIGER
    def get_lit(node: CandidateFunction) -> int:
        node_id = id(node)
        if node_id in node_to_lit:
            return node_to_lit[node_id]

        if node.node_type == NodeType.CONSTANT:
            assert node.value is not None
            return get_const_lit(node.value)

        if node.node_type == NodeType.LITERAL:
            assert node.value is not None
            q_var = abs(node.value)

            # This could be a universal variable (input) or an existential variable (wire)

            # Check if it's already mapped (Universal or previously computed Existential)
            if q_var in qdimacs_to_aiger_lit:
                base_lit = qdimacs_to_aiger_lit[q_var]

            # If it's an existential variable not yet computed, compute it on-demand
            elif q_var in candidates:
                # Cycle detection could be added here if needed, but assuming acyclic for now
                if q_var in visiting:
                    raise ValueError(f"Cycle detected involving variable {q_var}")

                visiting.add(q_var)
                # Compute the function for this existential variable
                base_lit = get_lit(candidates[q_var])
                visiting.remove(q_var)

                # Cache it
                qdimacs_to_aiger_lit[q_var] = base_lit

            elif q_var in outputs:
                # Existential variable but no candidate function?
                # Default to constant 0 (False)
                base_lit = get_const_lit(0)
                qdimacs_to_aiger_lit[q_var] = base_lit

            else:
                # Not a universal, not in candidates, not in outputs list?
                # Maybe a variable that is neither? (Unused quantifier?)

                # Check if it is a universal that we somehow missed?
                # (inputs list should cover all universals)
                raise ValueError(
                    f"Literal {q_var} found in candidate but not a known input or computed existential."
                )

            if node.value < 0:
                return base_lit ^ 1  # Negate
            return base_lit

        # Logic Gates
        if node.node_type == NodeType.AND:
            # Multi-input AND -> chain of binary ANDs
            lits = [get_lit(child) for child in node.children]
            if not lits:
                return get_const_lit(1)  # Empty AND is True

            curr_lit = lits[0]
            for next_lit in lits[1:]:
                # Create new AND gate: new_var = curr & next
                res_idx = new_aiger_var()
                res_lit = 2 * res_idx
                and_gates.append((res_lit, curr_lit, next_lit))
                curr_lit = res_lit

            node_to_lit[node_id] = curr_lit
            return curr_lit

        elif node.node_type == NodeType.OR:
            # a | b = ~(~a & ~b)
            lits = [get_lit(child) for child in node.children]
            if not lits:
                return get_const_lit(0)  # Empty OR is False

            # We want ~( (~l1) & (~l2) & ... )
            neg_lits = [l ^ 1 for l in lits]

            curr_lit = neg_lits[0]
            for next_lit in neg_lits[1:]:
                res_idx = new_aiger_var()
                res_lit = 2 * res_idx
                and_gates.append((res_lit, curr_lit, next_lit))
                curr_lit = res_lit

            # Result is negation of the AND chain
            res_lit = curr_lit ^ 1
            node_to_lit[node_id] = res_lit
            return res_lit

        elif node.node_type == NodeType.ITE:
            # ITE(c, t, f) = (c & t) | (~c & f)
            #              = ~( ~(c & t) & ~(~c & f) )
            #              = ~( ~(c & t) & ~(~c & f) )

            cond_lit = get_lit(node.children[0])
            true_lit = get_lit(node.children[1])
            false_lit = get_lit(node.children[2])

            # Term 1: c & t
            idx1 = new_aiger_var()
            t1_lit = 2 * idx1
            and_gates.append((t1_lit, cond_lit, true_lit))

            # Term 2: ~c & f
            idx2 = new_aiger_var()
            t2_lit = 2 * idx2
            and_gates.append((t2_lit, cond_lit ^ 1, false_lit))

            # OR them: ~( ~t1 & ~t2 )
            idx3 = new_aiger_var()
            term_and_lit = 2 * idx3
            and_gates.append((term_and_lit, t1_lit ^ 1, t2_lit ^ 1))

            res_lit = term_and_lit ^ 1
            node_to_lit[node_id] = res_lit
            return res_lit

        return get_const_lit(0)  # Should not reach

    # Collect output literals
    # We must output them in the order of 'outputs' (existential vars)
    output_lits = []
    for o_var in outputs:
        if o_var in candidates:
            out_lit = get_lit(candidates[o_var])
            output_lits.append(out_lit)
        else:
            # If no candidate, assume 0? Or 1?
            # Default to 0?
            print(
                f"Warning: No candidate for existential var {o_var}, defaulting to 0."
            )
            output_lits.append(get_const_lit(0))

    # Header parameters
    # const_one_var and const_zero_var created earlier.

    # Header parameters
    M = aiger_var_counter
    I = len(inputs)
    L = 0
    O = len(outputs) + 1 if include_result_output else len(outputs)
    A = len(and_gates)  # const one gate (already in and_gates)

    lines = []
    lines.append(f"aag {M} {I} {L} {O} {A}")

    # Inputs
    # They are 2, 4, ... 2*I
    for i in range(I):
        lines.append(str(2 * (i + 1)))

    # Latches (none)

    # Outputs
    for ol in output_lits:
        lines.append(str(ol))

    if include_result_output:
        # Result output (gate that evaluates to 1)
        lines.append(str(2 * const_one_var))

    # AND gates
    for lhs, rhs1, rhs2 in and_gates:
        lines.append(f"{lhs} {rhs1} {rhs2}")

    # Symbol Table
    # i0 QDIMACS_VAR ...
    for i, u_var in enumerate(inputs):
        lines.append(f"i{i} {u_var}")

    # o0 QDIMACS_VAR ...
    for i, e_var in enumerate(outputs):
        lines.append(f"o{i} {e_var}")

    if include_result_output:
        # Last output is result
        lines.append(f"o{len(outputs)} result")

    # Comments?
    lines.append("c")
    lines.append("Generated by 314 Solver")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Wrote AIG Skolem functions to {path}")
