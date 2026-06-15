import math

import embeddings


def test_l2_normalize_unit_length():
    v = embeddings.l2_normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-9)


def test_l2_normalize_zero_vector_is_safe():
    assert embeddings.l2_normalize([0.0, 0.0]) == [0.0, 0.0]


def test_cosine_identical_is_one():
    assert math.isclose(embeddings.cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, rel_tol=1e-9)


def test_cosine_orthogonal_is_zero():
    assert math.isclose(embeddings.cosine([1.0, 0.0], [0.0, 1.0]), 0.0, abs_tol=1e-9)
