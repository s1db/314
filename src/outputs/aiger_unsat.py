import logging
from typing import Dict, List, Tuple
from pathlib import Path
from src.instance import Instance

logger = logging.getLogger(__name__)


def write_aiger_unsat(
    path: Path,
    instance: Instance,
    cycle_assignments: List[Dict[int, bool]],
    include_result_output: bool = False,
):
    """
    Writes a Herbrand function to an ASCII AIGER file (.aag) for UNSAT instances.

    The Herbrand function utilizes the universal assignments from the unresolvable conflict cycle.
    For a given existential assignment Y, it outputs the first universal assignment X^{(i)}
    that falsifies the matrix.

    Adheres to the format expected by checkers/caqe_certcheck and standalone certcheck.
    1. Inputs: Existential variables (mapped to AIGER literals 2, 4, ..., 2*I).
    2. Outputs: Universal variables (mapped via symbol table).
    3. Symbol table: Maps AIGER inputs/outputs to QDIMACS variable IDs.
    """

    inputs: List[int] = instance.get_existential_vars()
    outputs: List[int] = instance.get_universal_vars()

    # Map Existential QDIMACS vars to AIGER literals (2, 4, ..., 2*I)
    qdimacs_to_aiger_lit_map: Dict[int, int] = {}
    for i, e_var in enumerate(inputs):
        qdimacs_to_aiger_lit_map[e_var] = 2 * (i + 1)

    aiger_var_counter = len(inputs)

    def new_aiger_var():
        nonlocal aiger_var_counter
        aiger_var_counter += 1
        return aiger_var_counter

    and_gates: List[Tuple[int, int, int]] = []

    # Create constant 0 and 1 gates to avoid using literal 0 and 1 directly in outputs
    const_zero_var = new_aiger_var()
    const_zero_lit = 2 * const_zero_var
    and_gates.append((const_zero_lit, 0, 0))

    const_one_var = new_aiger_var()
    const_one_lit = 2 * const_one_var
    and_gates.append((const_one_lit, 1, 1))

    def get_const_lit(val: bool) -> int:
        return const_one_lit if val else const_zero_lit

    def get_y_lit(qdimacs_lit: int) -> int:
        var = abs(qdimacs_lit)
        base = qdimacs_to_aiger_lit_map[var]
        if qdimacs_lit < 0:
            return base ^ 1
        return base

    def get_and_lit(lits: List[int]) -> int:
        if not lits:
            return const_one_lit
        if const_zero_lit in lits or 0 in lits:
            return const_zero_lit
        lits = [lit for lit in lits if lit != const_one_lit and lit != 1]
        if not lits:
            return const_one_lit

        curr_lit = lits[0]
        for next_lit in lits[1:]:
            res_idx = new_aiger_var()
            res_lit = 2 * res_idx
            and_gates.append((res_lit, curr_lit, next_lit))
            curr_lit = res_lit
        return curr_lit

    def get_or_lit(lits: List[int]) -> int:
        if not lits:
            return const_zero_lit
        if const_one_lit in lits or 1 in lits:
            return const_one_lit
        lits = [lit for lit in lits if lit != const_zero_lit and lit != 0]
        if not lits:
            return const_zero_lit

        neg_lits = [lit ^ 1 for lit in lits]
        res_lit = get_and_lit(neg_lits)
        return res_lit ^ 1

    def get_ite_lit(cond_lit: int, true_lit: int, false_lit: int) -> int:
        if cond_lit == const_one_lit or cond_lit == 1:
            return true_lit
        if cond_lit == const_zero_lit or cond_lit == 0:
            return false_lit
        if true_lit == false_lit:
            return true_lit

        t1_lit = get_and_lit([cond_lit, true_lit])
        t2_lit = get_and_lit([cond_lit ^ 1, false_lit])

        res_idx = new_aiger_var()
        term_and_lit = 2 * res_idx
        and_gates.append((term_and_lit, t1_lit ^ 1, t2_lit ^ 1))

        return term_and_lit ^ 1

    c_signals = []

    for i, X_assign in enumerate(cycle_assignments):
        clause_falsified_lits = []

        for clause in instance.clauses:
            clause_can_be_falsified = True
            y_lits_to_falsify = []

            for lit in clause:
                var = abs(lit)
                if var in outputs:  # Universal
                    val = X_assign.get(var, False)
                    lit_val = val if lit > 0 else not val
                    if lit_val:
                        clause_can_be_falsified = False
                        break
                elif var in inputs:  # Existential
                    y_lits_to_falsify.append(get_y_lit(-lit))

            if clause_can_be_falsified:
                cl_falsified = get_and_lit(y_lits_to_falsify)
                clause_falsified_lits.append(cl_falsified)

        matrix_falsified = get_or_lit(clause_falsified_lits)
        c_signals.append(matrix_falsified)

    output_lits = []

    for x_var in outputs:
        last_val = cycle_assignments[-1].get(x_var, False)
        out_xk = get_const_lit(last_val)

        for i in range(len(cycle_assignments) - 2, -1, -1):
            val = cycle_assignments[i].get(x_var, False)
            val_lit = get_const_lit(val)
            out_xk = get_ite_lit(c_signals[i], val_lit, out_xk)

        output_lits.append(out_xk)

    M = aiger_var_counter
    num_inputs = len(inputs)
    L = 0
    num_outputs = len(outputs) + 1 if include_result_output else len(outputs)
    A = len(and_gates)

    lines = []
    lines.append(f"aag {M} {num_inputs} {L} {num_outputs} {A}")

    # Standard AIGER inputs: 2, 4, ..., 2*I
    for i in range(num_inputs):
        lines.append(str(2 * (i + 1)))

    for ol in output_lits:
        lines.append(str(ol))

    if include_result_output:
        lines.append(
            "0"
        )  # Literal 0 specifies Herbrand/UNSAT strategy to caqe_certcheck

    for lhs, rhs1, rhs2 in and_gates:
        lines.append(f"{lhs} {rhs1} {rhs2}")

    for i, e_var in enumerate(inputs):
        lines.append(f"i{i} {e_var}")

    for i, u_var in enumerate(outputs):
        lines.append(f"o{i} {u_var}")

    if include_result_output:
        lines.append(f"o{len(outputs)} result")

    lines.append("c")
    lines.append("Generated by 314 Solver (UNSAT Certificate)")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Wrote Herbrand functions to {path}")
