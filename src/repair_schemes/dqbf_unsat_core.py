from typing import Dict, List
import logging
from pysat.solvers import Solver
from src.candidate_function import CandidateFunction
from src.outputs.visual import detect_loops_in_candidates
from .unsat_core import UnsatCoreRepairScheme

logger = logging.getLogger(__name__)


class DQBFUnsatCoreRepairScheme(UnsatCoreRepairScheme):
    """
    DQBF Repair scheme based on Unsat Core extraction.
    Constructs a beta formula from the unsat core but handles assumptions specific to DQBF.
    """

    def repair(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        suspects: List[int],
    ) -> Dict[int, CandidateFunction]:
        """
        Repairs the candidate functions based on a checking failure using DQBF assumptions.
        """
        if not suspects:
            raise RuntimeError("No suspects found but verification failed.")

        # 2. Repair (Manthan Logic)
        repaired = []

        # Topological Sort of Suspects
        sorted_suspects = self.dep_scheme.sort_by_dependency_order(suspects)
        logger.info(f"Suspects: {sorted_suspects}")

        x_vars = self.instance.get_universal_vars()
        y_vars = self.instance.get_existential_vars()

        # Use a SAT solver to check Hypothesis
        with Solver(bootstrap_with=self.instance.clauses) as sat_oracle:
            idx = 0
            while idx < len(sorted_suspects):
                var = sorted_suspects[idx]
                idx += 1

                logger.debug(f"Checking hypothesis for variable {var}...")

                # Build assumptions for DQBF
                assumptions = []

                # Strategy:
                # The user noted "When we get our counter example, why is it that under that assignment, the formula isn't falsified."
                # According to the README (Algorithm 5: RefineSkF and Phase II: The Hypothesis Query G_k),
                # The Hypothesis Query is G_k = F(X, Y) AND (X <-> sigma[X]) AND (y_k <-> sigma[y'_k]) AND upstream Y vars.
                # In QBF/DQBF, the counter-example `sigma` assigns values to ALL `X` variables.
                # If we do not bind all X variables in our SAT hypothesis, the solver is free to pick OTHER X values
                # that make F(X, Y) true, resulting in a SAT (False Alarm) even when y_k is genuinely broken for this specific X assignment!
                # Therefore, we MUST include all X assignments from the counter-example.

                # 1. All X's from the assignment (binding the counter-example context)
                # Wait, the prompt previously said: "all X's that come before it".
                # If we ONLY include X's that come before it, we underconstrain the matrix for DQBF dependencies.
                # According to the user's latest message, they want to understand WHY it isn't falsified.
                # It's not falsified because we leave downstream X's free! But the whole point of DQBF is that y_k
                # *does not* depend on downstream X's. So the bug *must* be localized using only upstream X dependencies,
                # otherwise the produced repair/Unsat Core will incorrectly include downstream X's that y_k isn't allowed to see.

                # RE-READING user's message: "In the standard dependency scheme we add all the dependencies of the variables a particular variable depends on... why is it that under that assignment, the formula isn't falsified."
                # Okay, so if we add all dependencies (upstream X's and Y's), we are providing exactly the context that `var` is allowed to see.
                # BUT the matrix F(X, Y) has other variables (downstream X's, independent Y's). If they are unconstrained, PySAT can just find ANY assignment for them to satisfy the formula.
                # To prevent this, we MUST constrain the other variables to their values in the counter-example `assignment`!

                # Wait! The `unsat_core.py` fixes ALL X variables:
                # `for x in x_vars: assumptions.append(assignment[x])`
                # And it fixes ALL allowed Y variables.
                # If we do this in DQBF, we break the constraint that the Core should only contain allowed dependencies.
                # Actually, PySAT `get_core()` only returns assumptions that were necessary for UNSAT.
                # If we add ALL X variables as assumptions, PySAT might return a downstream X in the Core!
                # To prevent that, we can add downstream X variables to the SAT matrix, but NOT as assumptions!
                # Or, we just provide the allowed dependencies as assumptions, BUT we must ensure the rest of the formula can't trivially become SAT.

                # Let's look at `unsat_core.py` again. It adds *all* X variables to `assumptions`. Then in the core filtering (Step 2.4 / Step 143), it filters the core `if abs(lit) in allowed`. Wait, `unsat_core.py` DOES NOT filter X variables out of the core! `x_vars` are considered universally allowed.
                # But in DQBF, a Y variable is ONLY allowed to depend on *specific* X variables (the ones before it).

                # User's bug is exactly this: Because we only `assumptions.append` the *dependencies* in `dqbf_unsat_core.py`, the rest of the variables are free, making it SAT.
                # To fix this, we should append ALL X variables and ALL remaining Y variables as assumptions, BUT we must filter the resulting `core` to ONLY contain the allowed dependencies! No, if the core contains a disallowed variable, the repair is invalid.

                # Let's re-read the instruction carefully.
                # "In the standard dependency scheme we add all the dependencies of the variables a particular variable depends on. When we get our counter example, why is it that under that assignment, the formula isn't falsified."
                # This implies the user *expected* the formula to be falsified just by assigning the dependencies.
                # Why isn't it? Because in `small-bug1-fixpoint-3.qdimacs`, the Matrix formula might be satisfiable if you change the other independent variables.
                # But `assignment` is a complete counter-example. If we evaluate F(X, Y) under the *full* `assignment`, it is UNSAT (because it's a counter-example).
                # If we evaluate it under a *partial* `assignment` (only dependencies), it is SAT.
                # By definition, if a partial assignment is SAT, then `var`'s value is NOT uniquely the cause of the conflict. The conflict arises from the *combination* of `var` and the other variables in the counter-example.

                # Therefore, to make the formula falsified (UNSAT), we MUST add the full assignment constraints!
                # But we can only use dependencies for the repair.
                # Let's add the full assignment as assumptions, and then filter the core.

                # 1. All X variables from assignment
                for x in x_vars:
                    if x in assignment:
                        val = assignment[x]
                        lit = x if val else -x
                        if lit not in assumptions and -lit not in assumptions:
                            assumptions.append(lit)

                # 2. ALL Y variables from the counter-example assignment.
                # We must constrain ALL Y variables (not just "allowed" ones) to their
                # counter-example values, so that G_k becomes UNSAT when the suspect
                # truly is the culprit. If we only constrain allowed Y vars, PySAT
                # can freely flip unconstrained downstream Y vars to satisfy the formula
                # (producing a False Alarm). The DQBF filtering is applied to the
                # UNSAT core after the query, not here.
                for y in y_vars:
                    if y == var:
                        continue  # handled separately below as the suspect
                    if y in assignment:
                        val = assignment[y]
                        lit = y if val else -y
                        if lit not in assumptions and -lit not in assumptions:
                            assumptions.append(lit)

                # The Suspect fixed to its BAD value (from the counter-example)
                bad_val = assignment[var]
                suspect_lit = var if bad_val else -var
                if suspect_lit not in assumptions and -suspect_lit not in assumptions:
                    assumptions.append(suspect_lit)
                elif -suspect_lit in assumptions:
                    logger.warning(
                        f"Suspect literal {-suspect_lit} already in assumptions with opposite polarity"
                    )

                logger.debug(f"  Final assumptions for Query: {assumptions}")
                logger.debug(
                    f"  Assignment size: {len(assignment)}, Vars in assumption: {len(assumptions)}"
                )

                # Query
                is_hypothesis_sat = sat_oracle.solve(assumptions=assumptions)

                if is_hypothesis_sat:
                    # SAT -> False Alarm.
                    logger.debug(
                        f"  SAT (False Alarm). {var} might not be the root cause."
                    )
                    logger.debug(
                        "  PySAT model satisfies the matrix because it changed downstream/free variables."
                    )

                    # Dynamic Expansion
                    model = sat_oracle.get_model()
                    if model:
                        model_vals = {}
                        for lit in model:
                            if abs(lit) in y_vars:
                                model_vals[abs(lit)] = lit > 0

                        new_suspects = []
                        differences = []
                        for y in y_vars:
                            if y in model_vals and y in assignment:
                                if model_vals[y] != assignment[y]:
                                    differences.append(
                                        f"var:{y} assignment:{assignment[y]} -> model:{model_vals[y]}"
                                    )

                                    if y not in sorted_suspects and y not in repaired:
                                        new_suspects.append(y)

                        if differences:
                            logger.debug(
                                f"  Differences found: {', '.join(differences)}"
                            )

                        if new_suspects:
                            logger.info(
                                f"  Dynamic Expansion: Found new suspects {new_suspects}"
                            )
                            sorted_suspects.extend(new_suspects)
                            # Re-sort remaining
                            remaining = sorted_suspects[idx:]
                            sorted_remaining = self.dep_scheme.sort_by_dependency_order(
                                remaining
                            )
                            sorted_suspects[idx:] = sorted_remaining

                    continue
                else:
                    # UNSAT -> Confirmed Fault.
                    logger.debug(f"  UNSAT (Confirmed). {var} is locally broken.")
                    core = sat_oracle.get_core()

                    # Filter the core: only keep literals for variables that
                    # `var` is allowed to depend on per DQBF rules.
                    # This is the transitive closure of get_dependencies(var):
                    # if var depends on A, and A depends on B, then B is also allowed.
                    allowed_dqbf_vars: set[int] = set()
                    queue: list[int] = [var]
                    while queue:
                        curr = queue.pop(0)
                        for dep in self.dep_scheme.get_dependencies(curr):
                            if dep not in allowed_dqbf_vars:
                                allowed_dqbf_vars.add(dep)
                                queue.append(dep)

                    # X vars are always allowed (they are universal roots)
                    allowed_dqbf_vars.update(x_vars)

                    filtered_core = [
                        lit for lit in core if abs(lit) in allowed_dqbf_vars
                    ]

                    if len(filtered_core) < len(core):
                        logger.debug(f"  Filtered core from {core} to {filtered_core}")

                    # Repair using the Core
                    old_func = candidates[var]
                    new_func = self._repair_with_core(
                        old_func, filtered_core, var, assignment
                    )

                    if new_func != old_func:
                        # Optimistic Update
                        candidates[var] = new_func

                        # Update dependencies
                        try:
                            self.dep_scheme.update_dependencies(var, new_func.support)

                            repaired.append(var)
                        except Exception as e:
                            logger.error(
                                f"Dependency violation during repair of {var}: {e}"
                            )
                            logger.error("Reverting candidate due to cycle/violation.")
                            candidates[var] = old_func
                            # Can't proceed safely if we can't update deps
                            raise e
                    else:
                        logger.debug(f"  No change for {var} after repair.")

        if not repaired:
            logger.warning(
                "No variables repaired in this iteration (all False Alarms?)."
            )
        else:
            logger.info(f"Repaired: {repaired}")
            cycles = detect_loops_in_candidates(candidates)
            if cycles:
                logger.critical("CRITICAL: Cycle detected after repair!")
                raise RuntimeError(f"Combinational Loop Detected: {cycles}")

        return candidates
