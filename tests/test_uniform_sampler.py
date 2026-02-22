from src.sampling_schemes.uniform import UniformSampler


def test_sampling():
    # (x1 v x2) & (-x1 v x3)
    clauses = [[1, 2], [-1, 3]]
    vars = [1, 2, 3]
    sampler = UniformSampler(vars, clauses)

    # Request 10 samples
    samples = sampler.sample(num_samples=10)

    # Check shape: (10, 3)
    assert samples.shape == (10, 3)
    assert samples.dtype == bool

    # Check validity
    for i in range(len(samples)):
        row = samples[i]
        # x1 = row[0], x2 = row[1], x3 = row[2]
        x1, x2, x3 = row

        # Check clauses
        # c1: x1 or x2
        sat1 = x1 or x2
        # c2: -x1 or x3
        sat2 = (not x1) or x3
        assert sat1 and sat2, f"Sample at row {i} ({row}) invalid"


def test_unsat():
    clauses = [[1], [-1]]
    vars = [1]
    sampler = UniformSampler(vars, clauses)
    samples = sampler.sample(num_samples=5)

    assert samples.shape == (0, 1)
    assert samples.dtype == bool
