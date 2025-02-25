from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import pandas as pd
from config.myconfig import Config
from config.mytable import TableSaver
from evotorch.logging import Logger
from problems.mis.mis_dataset import MISDataset
from problems.mis.mis_ga import MISGaProblem
from problems.mis.mis_instance import create_mis_instance
from problems.tsp.tsp_ga import TSPGAProblem
from problems.tsp.tsp_graph_dataset import TSPGraphDataset
from problems.tsp.tsp_instance import create_tsp_instance

from ea.ea_arg_parser import get_arg_parser

if TYPE_CHECKING:
    from argparse import ArgumentParser

    from config.myconfig import Config
    from evotorch import Problem
    from torch.utils.data import Dataset

    from ea.problem_instance import ProblemInstance


def filter_args_by_group(parser: ArgumentParser, group_name: str) -> dict:
    group = next((g for g in parser._action_groups if g.title == group_name), None)  # noqa: SLF001
    if group is None:
        error_msg = f"Group '{group_name}' not found"
        raise ValueError(error_msg)

    return [a.dest for a in group._group_actions]  # noqa: SLF001


def get_results_dict(config: Config, results: dict) -> None:
    # filter the name of the arguments of the grup ea_settings
    parser = get_arg_parser()
    ea_setting_args = filter_args_by_group(parser, "ea_settings")
    tsp_setting_args = filter_args_by_group(parser, "tsp_settings")
    mis_setting_args = filter_args_by_group(parser, "mis_settings")
    difusco_setting_args = filter_args_by_group(parser, "difusco_settings")
    dev_setting_args = filter_args_by_group(parser, "dev")

    row = {
        "task": config.task,
        "wandb_logger_name": config.wandb_logger_name,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }

    row.update({k: getattr(config, k) for k in ea_setting_args})
    row.update({k: getattr(config, k) for k in tsp_setting_args})
    row.update({k: getattr(config, k) for k in mis_setting_args})
    row.update({k: getattr(config, k) for k in difusco_setting_args})
    row.update({k: getattr(config, k) for k in dev_setting_args})
    row.update(results)

    return row


def dataset_factory(config: Config, split: str = "test") -> Dataset:
    if split == "train":
        split = "training"
    assert split in ["test", "training", "validation"], f"Invalid split: {split}"
    data_path = os.path.join(config.data_path, getattr(config, f"{split}_split"))
    data_label_dir = (
        os.path.join(config.data_path, getattr(config, f"{split}_split_label_dir"))
        if getattr(config, f"{split}_split_label_dir", None)
        else None
    )

    if config.task == "mis":
        return MISDataset(data_dir=data_path, data_label_dir=data_label_dir)

    if config.task == "tsp":
        return TSPGraphDataset(data_file=data_path, sparse_factor=config.sparse_factor)

    error_msg = f"No dataset for task {config.task}."
    raise ValueError(error_msg)


def instance_factory(config: Config, sample: tuple) -> ProblemInstance:
    if config.task == "mis":
        return create_mis_instance(sample, device=config.device)
    if config.task == "tsp":
        return create_tsp_instance(sample, device=config.device, sparse_factor=config.sparse_factor)
    error_msg = f"No instance for task {config.task}."
    raise ValueError(error_msg)


def problem_factory(task: str) -> Problem:
    if task == "mis":
        return MISGaProblem()
    if task == "tsp":
        return TSPGAProblem()
    error_msg = f"No problem for task {task}."
    raise ValueError(error_msg)


class CustomLogger(Logger):
    def __init__(
        self,
        table_name: str,
        instance_id: int,
        gt_cost: float,
        tmp_population_file: str,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(*args, **kwargs)
        self.keys_to_log = [
            "iter",
            "mean_eval",
            "median_eval",
            "pop_best_eval",
            "best_eval",
            "worst_eval",
        ]
        self.keys_to_plot = [k for k in self.keys_to_log if k != "iter"] + ["unique_solutions"]
        self.table_saver = TableSaver(table_name=table_name)
        self.instance_id = instance_id
        self.gt_cost = gt_cost
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.tmp_population_file = tmp_population_file

    def _log(self, status: dict) -> None:
        data = {k: status[k] for k in self.keys_to_log}
        data["instance_id"] = self.instance_id
        data["gt_cost"] = self.gt_cost
        data["timestamp"] = self.timestamp

        with open(self.tmp_population_file) as f:
            pop_str = f.readlines()[-1].strip()
            solution_strs = pop_str.split(" | ")
            data["unique_solutions"] = len(set(solution_strs))

        self.table_saver.put(data)

    def save_evolution_figure(self) -> None:
        table_name = self.table_saver.table_name
        df = pd.read_csv(table_name)
        df = df[df["timestamp"] == self.timestamp]

        # Create figure and primary axis
        fig, ax1 = plt.subplots()

        # Plot all metrics except unique_solutions and iter on primary axis
        keys_to_plot = [k for k in self.keys_to_log if k not in ["iter", "unique_solutions"]]
        for key in keys_to_plot:
            ax1.plot(df["iter"], df[key], label=key, linewidth=1.5)
        ax1.set_xlabel("Iterations")
        ax1.set_ylabel("Fitness Values")

        # Create secondary axis for unique_solutions
        ax2 = ax1.twinx()
        ax2.plot(
            df["iter"],
            df["unique_solutions"],
            label="unique_solutions",
            color="red",
            linestyle=":",
            linewidth=1,
            alpha=0.7,
        )
        ax2.set_ylabel("Number of Unique Solutions")

        # Scale the unique solutions axis to avoid exaggerated fluctuations
        unique_min = df["unique_solutions"].min()
        unique_max = df["unique_solutions"].max()
        ax2.set_ylim(unique_min * 0.95, unique_max * 1.05)

        # Force integer ticks on the right axis
        ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        # Combine legends from both axes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right")

        plt.tight_layout()
        plt.savefig(f"{table_name.replace('.csv', '')}_{self.timestamp}.png")
        plt.close()
