from typing import Dict, List
import logging
from pysat.solvers import Solver
from src.candidate_function import CandidateFunction
from .base import RepairScheme
from src.outputs.visual import detect_loops_in_candidates

logger = logging.getLogger(__name__)


class UnsatCoreRepairScheme(RepairScheme):
    """
    Repair scheme based on Unsat Core extraction.
    Constructs a beta formula from the unsat core of (Matrix + Dependencies + BadValue)
    and patches the function.
    """

    def repair(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        suspects: List[int],
    ) -> Dict[int, CandidateFunction]:
        """
        Repairs the candidate functions based on a checking failure.
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

                # Step B: Construct Hypothesis Query
                assumptions = []
                # Always fix X variables from assignment (they are upstream roots)
                for x in x_vars:
                    if x in assignment:
                        val = assignment[x]
                        assumptions.append(x if val else -x)

                for y in y_vars:
                    if y == var:
                        continue  # handled separately below as the suspect
                    if y in assignment:
                        val = assignment[y]
                        assumptions.append(y if val else -y)

                # The Suspect fixed to BAD value
                bad_val = assignment[var]
                assumptions.append(var if bad_val else -var)

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

                    # Repair using the Core
                    old_func = candidates[var]
                    new_func = self._repair_with_core(old_func, core, var, assignment)

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

    def _repair_with_core(self, candidate, core, variable, assignment):
        """
        Repairs the candidate using a provided UNSAT core.
        """
        # Filter Core using Dependency Scheme
        allowed_vars = None
        if variable is not None:
            allowed_vars = self.dep_scheme.get_allowed_variables(variable)

        beta_children = []
        for lit in core:
            var = abs(lit)
            if var == variable:
                continue

            if allowed_vars is not None:
                if var not in allowed_vars:
                    # Skip forbidden dependency
                    continue

            node = self.function_manager.get_lit(lit)
            beta_children.append(node)

        if not beta_children:
            beta_function = None  # Represents True
        else:
            beta_function = self.function_manager.get_and(beta_children)

        # Patch Candidate
        bad_val = assignment[variable]

        if not bad_val:  # Bad is 0 (False), want to make it True
            # New = Old OR Beta
            if beta_function is None:
                # Beta is True. Old OR True = True.
                return self.function_manager.get_true()
            else:
                return self.function_manager.get_or([candidate, beta_function])
        else:  # Bad is 1 (True), want to make it False
            # New = Old AND NOT Beta
            if beta_function is None:
                # Beta is True. NOT Beta is False. Old AND False = False.
                return self.function_manager.get_false()
            else:
                not_beta = beta_function.Not(self.function_manager)
                return self.function_manager.get_and([candidate, not_beta])
