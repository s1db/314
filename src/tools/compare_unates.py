"""Comparison tool for unate detection algorithms."""

import argparse
import logging
import time
from pathlib import Path

from src.instance_parsers.qbf import QBFParser
from src.instance import Instance
from src.candidate_function import FunctionManager
from src.preprocessing.manthan_unate import ManthanUnatePreprocessor
from src.preprocessing.guess_unate import GuessUnatePreprocessor
from src.sampling_schemes.uniform import UniformSampler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compare_unates")


def run_preprocessor(preprocessor, instance: Instance, samples=None):
    candidates = {}
    function_manager = FunctionManager()

    start_time = time.time()
    preprocessor.run(
        instance.clauses,
        instance.get_universal_vars(),
        instance.get_existential_vars(),
        candidates,
        function_manager,
        samples=samples,
    )
    end_time = time.time()

    pos_unates = [v for v, f in candidates.items() if f.is_true]
    neg_unates = [v for v, f in candidates.items() if f.is_false]

    return {
        "pos": sorted(pos_unates),
        "neg": sorted(neg_unates),
        "time": end_time - start_time,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", type=Path)
    parser.add_argument("--samples", type=int, default=500)
    args = parser.parse_args()

    instance = QBFParser.from_file(args.instance)
    all_vars = sorted(instance.get_universal_vars() + instance.get_existential_vars())

    logger.info(f"Generating {args.samples} samples...")
    sampler = UniformSampler(all_vars, instance.clauses)
    samples = sampler.sample(args.samples)

    logger.info("Running ManthanUnatePreprocessor...")
    manthan = ManthanUnatePreprocessor()
    res_manthan = run_preprocessor(manthan, instance)

    logger.info("Running GuessUnatePreprocessor (verify=True)...")
    guess_v = GuessUnatePreprocessor(verify=True)
    res_guess_v = run_preprocessor(guess_v, instance, samples=samples)

    logger.info("Running GuessUnatePreprocessor (verify=False)...")
    guess_nv = GuessUnatePreprocessor(verify=False)
    res_guess_nv = run_preprocessor(guess_nv, instance, samples=samples)

    print("\n--- RESULTS ---")
    print(f"File: {args.instance.name}")
    print(f"{'Method':<25} | {'Pos':<5} | {'Neg':<5} | {'Time (s)':<10}")
    print("-" * 55)
    print(
        f"{'Manthan (Definability)':<25} | {len(res_manthan['pos']):<5} | {len(res_manthan['neg']):<5} | {res_manthan['time']:.4f}"
    )
    print(
        f"{'Guess (Sampling + Verify)':<25} | {len(res_guess_v['pos']):<5} | {len(res_guess_v['neg']):<5} | {res_guess_v['time']:.4f}"
    )
    print(
        f"{'Guess (Sampling Only)':<25} | {len(res_guess_nv['pos']):<5} | {len(res_guess_nv['neg']):<5} | {res_guess_nv['time']:.4f}"
    )

    # Check consistency
    if (
        res_manthan["pos"] != res_guess_v["pos"]
        or res_manthan["neg"] != res_guess_v["neg"]
    ):
        print("\nWARNING: Manthan and Guess (Verified) results differ!")
        print(f"Manthan Pos: {res_manthan['pos']}")
        print(f"Guess V Pos: {res_guess_v['pos']}")
        print(f"Manthan Neg: {res_manthan['neg']}")
        print(f"Guess V Neg: {res_guess_v['neg']}")


if __name__ == "__main__":
    main()
