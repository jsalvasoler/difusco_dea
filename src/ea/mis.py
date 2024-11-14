from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import torch
from evotorch import Problem
from evotorch.algorithms import GeneticAlgorithm
from evotorch.operators import GaussianMutation, OnePointCrossOver

from difusco.mis.utils import mis_decode_torch

if TYPE_CHECKING:
    import numpy as np

    from ea.config import Config


class MISInstance:
    def __init__(self, adj_matrix: torch.Tensor, n_nodes: int, gt_labels: np.array | None = None) -> None:
        self.adj_matrix = adj_matrix
        self.n_nodes = n_nodes
        self.gt_labels = gt_labels

    def evaluate_mis_individual(self, ind: torch.Tensor) -> float:
        return mis_decode_torch(ind, self.adj_matrix).sum()


def create_mis_ea(instance: MISInstance, config: Config) -> GeneticAlgorithm:
    problem = Problem(
        objective_func=instance.evaluate_mis_individual,
        objective_sense="max",
        solution_length=instance.n_nodes,
        bounds=(0, 1),
    )

    return GeneticAlgorithm(
        problem=problem,
        popsize=config.pop_size,
        operators=[
            OnePointCrossOver(problem, tournament_size=4),
            GaussianMutation(problem, stdev=0.1),
        ],
        re_evaluate=False,
    )


def create_mis_instance(sample: tuple, device: Literal["cpu", "cuda"] = "cpu") -> MISInstance:
    _, graph_data, _ = sample

    edge_index = graph_data.edge_index
    values = torch.ones(edge_index.shape[1], dtype=torch.float32)
    adj_mat_sparse = torch.sparse_coo_tensor(
        edge_index, values, (graph_data.x.shape[0], graph_data.x.shape[0]), device=device
    ).to_sparse_csr()

    return MISInstance(adj_mat_sparse, graph_data.x.shape[0], graph_data.x)
