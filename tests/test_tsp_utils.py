# ruff: noqa: N806

from itertools import permutations

import numpy as np
from resources.tsp_merge_python import merge_python

from difusco.tsp.utils import batched_two_opt_torch, merge_cython


def adj_mat_to_tour(adj_mat: np.ndarray) -> list:
    N = adj_mat.shape[0]
    tour = [0]
    while len(tour) < N + 1:
        n = np.nonzero(adj_mat[tour[-1]])[0]
        if len(tour) > 1:
            n = n[n != tour[-2]]
        tour.append(n.max())
    return tour


def test_merge_python_is_same_as_cython() -> None:
    # Example usage with simple coordinates
    coords = np.array([[0, 0], [1, 1], [2, 0], [1, -1]], dtype=float)
    # set random seed for reproducibility
    np.random.seed(0)
    adj_mat = np.random.rand(4, 4)

    # Symmetrize adj_mat to make it suitable for a tour
    adj_mat = (adj_mat + adj_mat.T) / 2

    A_1, iterations_1 = merge_python(coords, adj_mat)
    print("\nResulting Adjacency Matrix:")
    print(A_1)
    print(f"Total merge iterations: {iterations_1}")

    tour_1 = adj_mat_to_tour(A_1)
    print("\nExtracted Tour:")
    print(tour_1)

    # now use merge_cython
    A_2, iterations_2 = merge_cython(coords, adj_mat)
    print("\nResulting Adjacency Matrix:")
    print(A_2)
    print(f"Total merge iterations: {iterations_2}")

    tour_2 = adj_mat_to_tour(A_2)
    print("\nExtracted Tour:")
    print(tour_2)

    assert iterations_1 == iterations_2
    assert tour_1 == tour_2
    assert np.array_equal(A_1, A_2)


def test_cython_merge_solves_correctly() -> None:
    # Example usage with simple coordinates
    coords = np.array([[0, 0], [1, 1], [2, 0], [1, -1]], dtype=float)
    # set random seed for reproducibility
    np.random.seed(0)
    adj_mat = np.array([[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 1, 0]], dtype=float)

    # add 0.001 everywhere except where there are ones
    adj_mat[adj_mat == 0] = 0.001

    A, iterations = merge_python(coords, adj_mat)
    print("\nResulting Adjacency Matrix:")
    print(A)
    print(f"Total merge iterations: {iterations}")

    tour = adj_mat_to_tour(A)
    print("\nExtracted Tour:")
    print(tour)
    assert tour in ([0, 1, 2, 3, 0], [0, 3, 2, 1, 0])


def test_batched_two_opt_torch() -> None:
    # Example usage with simple coordinates
    coords = np.array([[0, 0], [1, 1], [2, 0], [1, -1]], dtype=float)
    dist = np.linalg.norm(coords[:, None] - coords, axis=-1)
    # set random seed for reproducibility
    np.random.seed(0)
    adj_mat = np.random.rand(4, 4)
    # Symmetrize adj_mat to make it suitable for a tour
    adj_mat = (adj_mat + adj_mat.T) / 2

    # Compute optimal tour by enumerating all permutations
    def get_optimal_tour(dist: np.ndarray) -> tuple:
        min_cost = np.inf
        min_tour = None
        for perm in permutations(range(1, 4)):
            # compute cost
            tour = [0, *list(perm)]
            cost = sum(dist[tour[i], tour[i + 1]] for i in range(len(tour) - 1)) + dist[tour[-1], tour[0]]
            if cost < min_cost:
                min_cost = cost
                min_tour = tour
        return [*min_tour, 0], min_cost

    min_tour, min_cost = get_optimal_tour(dist)

    print("\nOptimal Tour:")
    print(min_tour)
    print(f"Cost: {min_cost}")

    batched_tours = np.array([[0, 1, 2, 3, 0], [3, 2, 1, 0, 3], [0, 1, 3, 2, 0], [0, 2, 3, 1, 0]], dtype=int)
    solved_tours, iterations = batched_two_opt_torch(coords, batched_tours, max_iterations=1000)
    print("\nSolved Tours:")
    print(solved_tours)
    print(f"Total 2-opt iterations: {iterations}")

    # assert that all tours equal the min_tour
    edges_min_cost = np.array([min_tour[i : i + 2] for i in range(len(min_tour) - 1)])
    edges_min_cost += edges_min_cost[:, ::-1]
    for tour in solved_tours:
        edges = np.array([tour[i : i + 2] for i in range(len(tour) - 1)])
        edges += edges[:, ::-1]
        assert sorted(edges.tolist()) == sorted(edges_min_cost.tolist()), f"{edges} != {edges_min_cost}"


if __name__ == "__main__":
    test_merge_python_is_same_as_cython()
    # test_cython_merge_solves_correctly()
    # test_batched_two_opt_torch()
