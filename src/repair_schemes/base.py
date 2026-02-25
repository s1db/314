from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

from pysat.solvers import Solver

from src.candidate_function import CandidateFunction, FunctionManager
from src.instance import Instance
from src.outputs.visual import detect_loops_in_candidates

logger = logging.getLogger(__name__)


class RepairScheme(ABC):
    """
    Abstract base class for repair schemes.

    Provides a concrete ``repair()`` implementation that performs the
    standard hypothesis-checking loop (SAT/UNSAT classification, dynamic
    expansion, patching, cycle detection).  Subclasses only need to
    implement ``_compute_beta`` which determines *how* the repair patch
    is computed once a suspect is confirmed as locally broken.

    Subclasses may override ``repair()`` entirely if they require a
    fundamentally different repair paradigm.
    """

    def __init__(
        self,
        instance: Instance,
        dependency_scheme: Any,
        function_manager: FunctionManager,
    ):
        self.instance = instance
        self.dep_scheme = dependency_scheme
        self.function_manager = function_manager

    # ------------------------------------------------------------------
    #  Template repair loop
    # ------------------------------------------------------------------

    def repair(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        suspects: List[int],
    ) -> Dict[int, CandidateFunction]:
        """
        Repairs the candidate functions based on a checking failure.

        For each suspect (in dependency order) the method checks whether
        fixing the suspect to its *bad* value under the current assignment
        is UNSAT (i.e. locally broken).  If so, ``_compute_beta`` is
        called to obtain a beta formula and the candidate is patched.
        If the hypothesis is SAT (false alarm), dynamic expansion may
        discover new suspects.

        Args:
            candidates: The current candidate functions.
            assignment: Counter-example assignment (var → bool).
            suspects: Suspect variable IDs from fault localization.

        Returns:
            The updated candidate functions.
        """
        if not suspects:
            logger.error("Error: No suspects found but verification failed.")
            return candidates

        repaired: List[int] = []

        sorted_suspects = self.dep_scheme.sort_by_dependency_order(suspects)
        logger.info(f"Suspects: {sorted_suspects}")

        x_vars = self.instance.get_universal_vars()
        y_vars = self.instance.get_existential_vars()

        with Solver(bootstrap_with=self.instance.clauses) as sat_oracle:
            idx = 0
            while idx < len(sorted_suspects):
                var = sorted_suspects[idx]
                idx += 1

                logger.debug(f"Checking hypothesis for variable {var}...")

                # Step A: Allowed / Upstream variables
                allowed = self.dep_scheme.get_allowed_variables(var)

                # Step B: Build assumptions
                assumptions: List[int] = []
                for x in x_vars:
                    if x in assignment:
                        val = assignment[x]
                        assumptions.append(x if val else -x)

                for y in y_vars:
                    if y in allowed:
                        if y in assignment:
                            val = assignment[y]
                            assumptions.append(y if val else -y)

                bad_val = assignment[var]
                assumptions.append(var if bad_val else -var)

                is_hypothesis_sat = sat_oracle.solve(assumptions=assumptions)

                if is_hypothesis_sat:
                    # SAT → False Alarm
                    logger.debug(
                        f"  SAT (False Alarm). {var} might not be the root cause."
                    )

                    # Dynamic Expansion
                    model = sat_oracle.get_model()
                    if model:
                        model_vals: Dict[int, bool] = {}
                        for lit in model:
                            if abs(lit) in y_vars:
                                model_vals[abs(lit)] = lit > 0

                        new_suspects: List[int] = []
                        for y in y_vars:
                            if y in model_vals and y in assignment:
                                if model_vals[y] != assignment[y]:
                                    if y not in sorted_suspects and y not in repaired:
                                        new_suspects.append(y)

                        if new_suspects:
                            logger.info(
                                f"  Dynamic Expansion: Found new suspects {new_suspects}"
                            )
                            sorted_suspects.extend(new_suspects)
                            remaining = sorted_suspects[idx:]
                            sorted_remaining = self.dep_scheme.sort_by_dependency_order(
                                remaining
                            )
                            sorted_suspects[idx:] = sorted_remaining

                    continue
                else:
                    # UNSAT → Confirmed Fault
                    logger.debug(f"  UNSAT (Confirmed). {var} is locally broken.")

                    old_func = candidates[var]
                    beta = self._compute_beta(
                        old_func, var, assignment, allowed, sat_oracle
                    )
                    new_func = self._apply_patch(old_func, beta, assignment[var])

                    if new_func != old_func:
                        candidates[var] = new_func

                        try:
                            self.dep_scheme.update_dependencies(var, new_func.support)
                            repaired.append(var)
                        except Exception as e:
                            logger.error(
                                f"Dependency violation during repair of {var}: {e}"
                            )
                            logger.error("Reverting candidate due to cycle/violation.")
                            candidates[var] = old_func
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

    # ------------------------------------------------------------------
    #  Patching
    # ------------------------------------------------------------------

    def _apply_patch(
        self,
        candidate: CandidateFunction,
        beta: Optional[CandidateFunction],
        bad_value: bool,
    ) -> CandidateFunction:
        """Apply the beta patch to a candidate function.

        If ``bad_value`` is False (the current value is wrong-low),
        the patch is ``old OR beta``.  If True (wrong-high), the patch
        is ``old AND NOT beta``.

        Args:
            candidate: The current candidate function.
            beta: The beta (correction) formula, or *None* meaning True.
            bad_value: The bad value of the suspect under the assignment.

        Returns:
            The patched candidate function.
        """
        fm = self.function_manager

        if not bad_value:  # Bad is False → want True → new = old OR beta
            if beta is None:
                return fm.get_true()
            else:
                return fm.get_or([candidate, beta])
        else:  # Bad is True → want False → new = old AND NOT beta
            if beta is None:
                return fm.get_false()
            else:
                not_beta = beta.Not(fm)
                return fm.get_and([candidate, not_beta])

    # ------------------------------------------------------------------
    #  Abstract hook
    # ------------------------------------------------------------------

    @abstractmethod
    def _compute_beta(
        self,
        candidate: CandidateFunction,
        variable: int,
        assignment: Dict[int, bool],
        allowed_vars: "set[int]",
        sat_oracle: Solver,
    ) -> Optional[CandidateFunction]:
        """Compute the beta (correction) formula for a confirmed suspect.

        Called only when the hypothesis query for *variable* is UNSAT.
        Must return a ``CandidateFunction`` representing the beta formula,
        or ``None`` to represent the constant True.

        Args:
            candidate: The current candidate function for *variable*.
            variable: The suspect variable ID.
            assignment: The counter-example assignment (var → bool).
            allowed_vars: Variables that *variable* is allowed to depend on.
            sat_oracle: The SAT solver (hypothesis was just UNSAT; the
                core may still be available via ``sat_oracle.get_core()``).

        Returns:
            The beta correction formula, or None (meaning True).
        """
        ...
