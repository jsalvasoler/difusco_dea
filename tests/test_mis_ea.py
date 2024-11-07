import os

import torch
from ea.mis import MISInstance, create_mis_ea, create_mis_instance
from evotorch import Problem

from difusco.mis.mis_dataset import MISDataset


def read_mis_instance() -> MISInstance:
    resource_dir = "tests/resources"
    dataset = MISDataset(
        data_dir=os.path.join(resource_dir, "er_example_dataset"),
        data_label_dir=os.path.join(resource_dir, "er_example_dataset_annotations"),
    )

    sample = dataset.__getitem__(0)

    return create_mis_instance(sample)


def test_create_mis_instance() -> None:
    instance = read_mis_instance()
    assert instance.n_nodes == 732
    assert instance.gt_labels.sum().item() == 45
    assert (
        instance.gt_labels.shape[0]
        == 732
        == instance.n_nodes
        == instance.adj_matrix.shape[0]
        == instance.adj_matrix.shape[1]
    )


def test_mis_ga_runs() -> None:
    instance = read_mis_instance()

    ga = create_mis_ea(instance)
    ga.run(2)

    status = ga.status
    assert status["iter"] == 2


def test_mis_problem_evaluation() -> None:
    instance = read_mis_instance()

    problem = Problem(
        objective_func=instance.evaluate_mis_individual,
        objective_sense="max",
        solution_length=instance.n_nodes,
    )

    # create ind as a random tensor with size n_nodes
    ind = torch.rand(instance.n_nodes)
    obj = instance.evaluate_mis_individual(ind)
    assert obj == problem._objective_func(ind)  # noqa: SLF001

    # evaluate the labels (ground truth) of the instance
    obj_gt = instance.evaluate_mis_individual(instance.gt_labels)
    assert obj_gt == problem._objective_func(instance.gt_labels)  # noqa: SLF001

    assert obj_gt == instance.gt_labels.sum()
    assert obj_gt >= obj
