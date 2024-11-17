from __future__ import annotations

import warnings
from multiprocessing import Pool
from typing import Literal  # TODO: fix when upgrading python version

import numpy as np
import scipy.sparse
import scipy.spatial
import torch
from problems.tsp.cython_merge.cython_merge import merge_cython


def batched_two_opt_torch(
    points: np.ndarray, tour: np.ndarray, max_iterations: int = 1000, device: Literal["cpu", "gpu"] = "cpu"
) -> tuple[np.ndarray, int]:
    """
    Apply the 2-opt algorithm to a batch of tours.
    Tours have N + 1 elements, i.e., the first city is repeated at the end.
    """

    iterator = 0
    tour = tour.copy()

    with torch.inference_mode():
        cuda_points = torch.from_numpy(points).to(device)
        cuda_tour = torch.from_numpy(tour).to(device)
        batch_size = cuda_tour.shape[0]

        min_change = -1.0
        while min_change < 0.0:
            points_i = cuda_points[cuda_tour[:, :-1].reshape(-1)].reshape((batch_size, -1, 1, 2))
            points_j = cuda_points[cuda_tour[:, :-1].reshape(-1)].reshape((batch_size, 1, -1, 2))
            points_i_plus_1 = cuda_points[cuda_tour[:, 1:].reshape(-1)].reshape((batch_size, -1, 1, 2))
            points_j_plus_1 = cuda_points[cuda_tour[:, 1:].reshape(-1)].reshape((batch_size, 1, -1, 2))

            A_ij = torch.sqrt(torch.sum((points_i - points_j) ** 2, axis=-1))
            A_i_plus_1_j_plus_1 = torch.sqrt(torch.sum((points_i_plus_1 - points_j_plus_1) ** 2, axis=-1))
            A_i_i_plus_1 = torch.sqrt(torch.sum((points_i - points_i_plus_1) ** 2, axis=-1))
            A_j_j_plus_1 = torch.sqrt(torch.sum((points_j - points_j_plus_1) ** 2, axis=-1))

            change = A_ij + A_i_plus_1_j_plus_1 - A_i_i_plus_1 - A_j_j_plus_1
            valid_change = torch.triu(change, diagonal=2)

            min_change = torch.min(valid_change)
            flatten_argmin_index = torch.argmin(valid_change.reshape(batch_size, -1), dim=-1)
            min_i = torch.div(flatten_argmin_index, len(points), rounding_mode="floor")
            min_j = torch.remainder(flatten_argmin_index, len(points))

            if min_change < -1e-6:
                for i in range(batch_size):
                    cuda_tour[i, min_i[i] + 1 : min_j[i] + 1] = torch.flip(
                        cuda_tour[i, min_i[i] + 1 : min_j[i] + 1], dims=(0,)
                    )
                iterator += 1
            else:
                break

            if iterator >= max_iterations:
                break

        tour = cuda_tour.cpu().numpy()

    return tour, iterator


def numpy_merge(points: np.ndarray, adj_mat: np.ndarray) -> tuple[np.ndarray, int]:
    """Currently unused. Supposed to be a numpy implementation of the cython merge function."""
    dists = np.linalg.norm(points[:, None] - points, axis=-1)

    components = np.zeros((adj_mat.shape[0], 2)).astype(int)
    components[:] = np.arange(adj_mat.shape[0])[..., None]
    real_adj_mat = np.zeros_like(adj_mat)
    merge_iterations = 0
    for edge in (-adj_mat / dists).flatten().argsort():
        merge_iterations += 1
        a, b = edge // adj_mat.shape[0], edge % adj_mat.shape[0]
        if not (a in components and b in components):
            continue
        ca = np.nonzero((components == a).sum(1))[0][0]
        cb = np.nonzero((components == b).sum(1))[0][0]
        if ca == cb:
            continue
        cca = sorted(components[ca], key=lambda x: x == a)
        ccb = sorted(components[cb], key=lambda x: x == b)
        newc = np.array([[cca[0], ccb[0]]])
        m, M = min(ca, cb), max(ca, cb)
        real_adj_mat[a, b] = 1
        components = np.concatenate([components[:m], components[m + 1 : M], components[M + 1 :], newc], 0)
        if len(components) == 1:
            break
    real_adj_mat[components[0, 1], components[0, 0]] = 1
    real_adj_mat += real_adj_mat.T
    return real_adj_mat, merge_iterations


def cython_merge(points: np.ndarray, adj_mat: np.ndarray) -> tuple[np.ndarray, int]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        real_adj_mat, merge_iterations = merge_cython(points.astype("double"), adj_mat.astype("double"))
        real_adj_mat = np.asarray(real_adj_mat)
        return real_adj_mat, merge_iterations


def merge_tours(
    adj_mat: np.ndarray,
    np_points: np.ndarray,
    edge_index_np: np.ndarray,
    sparse_graph: bool = False,
    parallel_sampling: int = 1,
) -> tuple[list, float]:
    """
    Merge tours using the cython implementation of the merge function.

    Args:
        ajd_mat: P x N x N array of adjacency matrices. P parallel samples, N number of nodes.
        np_points: N x 2 array of node coordinates.
        edge_index_np: 2 x E array of edges. Only used if sparse_graph is True.
        parallel_sampling: Number of parallel samples to run (= P).

    Returns:
        tours: List of tours. Each tour is a list of node indices.
        merge_iterations: Average number of merge iterations across all samples.
    """
    splitted_adj_mat = np.split(adj_mat, parallel_sampling, axis=0)

    if not sparse_graph:
        splitted_adj_mat = [adj_mat[0] + adj_mat[0].T for adj_mat in splitted_adj_mat]
    else:
        splitted_adj_mat = [
            scipy.sparse.coo_matrix(
                (adj_mat, (edge_index_np[0], edge_index_np[1])),
            ).toarray()
            + scipy.sparse.coo_matrix(
                (adj_mat, (edge_index_np[1], edge_index_np[0])),
            ).toarray()
            for adj_mat in splitted_adj_mat
        ]

    splitted_points = [np_points for _ in range(parallel_sampling)]

    if np_points.shape[0] > 1000 and parallel_sampling > 1:
        with Pool(parallel_sampling) as p:
            results = p.starmap(
                cython_merge,
                zip(splitted_points, splitted_adj_mat),
            )
    else:
        results = [
            cython_merge(_np_points, _adj_mat) for _np_points, _adj_mat in zip(splitted_points, splitted_adj_mat)
        ]

    splitted_real_adj_mat, splitted_merge_iterations = zip(*results)

    tours = []
    for i in range(parallel_sampling):
        tour = [0]
        while len(tour) < splitted_adj_mat[i].shape[0] + 1:
            n = np.nonzero(splitted_real_adj_mat[i][tour[-1]])[0]
            if len(tour) > 1:
                n = n[n != tour[-2]]
            tour.append(n.max())
        tours.append(tour)

    merge_iterations = np.mean(splitted_merge_iterations)
    return tours, merge_iterations


class TSPEvaluator:
    def __init__(self, points: np.ndarray) -> None:
        self.dist_mat = scipy.spatial.distance_matrix(points, points)

    def evaluate(self, route: np.array) -> float:
        total_cost = 0
        for i in range(len(route) - 1):
            total_cost += self.dist_mat[route[i], route[i + 1]]
        return total_cost


class TSPTorchEvaluator:
    def __init__(self, points: torch.Tensor) -> None:
        self.dist_mat = torch.cdist(points, points).to(points.device)

    def evaluate(self, route: torch.Tensor) -> float:
        # Get the consecutive pairs of indices from the route (e.g., [route[i], route[i+1]])
        route_pairs = torch.stack([route[:-1], route[1:]], dim=1)

        # Use gather to select the distances between consecutive points along the route
        distances = self.dist_mat[route_pairs[:, 0], route_pairs[:, 1]]

        # Sum the distances to get the total route cost
        return distances.sum().item()
