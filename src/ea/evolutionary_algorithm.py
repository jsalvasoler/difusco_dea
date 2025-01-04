from __future__ import annotations

import multiprocessing as mp
import timeit
from typing import TYPE_CHECKING, Any

import numpy as np
import torch
import wandb
from config.myconfig import Config
from config.mytable import TableSaver
from evotorch.logging import StdOutLogger
from problems.mis.mis_brkga import create_mis_brkga
from problems.mis.mis_ga import create_mis_ga
from problems.tsp.tsp_brkga import create_tsp_brkga
from problems.tsp.tsp_ga import create_tsp_ga
from pyinstrument import Profiler
from torch_geometric.loader import DataLoader
from tqdm import tqdm

from ea.ea_utils import dataset_factory, get_results_dict, instance_factory

if TYPE_CHECKING:
    from argparse import Namespace

    from evotorch.algorithms import GeneticAlgorithm

    from ea.problem_instance import ProblemInstance


def ea_factory(config: Config, instance: ProblemInstance) -> GeneticAlgorithm:
    if config.algo == "brkga":
        if config.task == "mis":
            return create_mis_brkga(instance, config)
        if config.task == "tsp":
            return create_tsp_brkga(instance, config)
    elif config.algo == "ga":
        if config.task == "mis":
            return create_mis_ga(instance, config)
        if config.task == "tsp":
            return create_tsp_ga(instance, config)
    error_msg = f"No evolutionary algorithm for task {config.task}."
    raise ValueError(error_msg)


def main_ea(args: Namespace) -> None:
    config = Config.load_from_args(args)

    if args.profiler:
        with Profiler() as profiler:
            run_ea(config)
        print(profiler.output_text(unicode=True, color=True))
    else:
        run_ea(config)


def run_single_iteration(config: Config, sample: Any) -> dict:  # noqa: ANN401
    instance = instance_factory(config, sample)
    ea = ea_factory(config, instance)

    _ = StdOutLogger(searcher=ea, interval=10, after_first_step=True)

    start_time = timeit.default_timer()
    ea.run(config.n_generations)

    cost = ea.status["pop_best_eval"]
    gt_cost = instance.get_gt_cost()

    diff = cost - gt_cost if ea.problem.objective_sense == "min" else gt_cost - cost
    gap = diff / gt_cost

    results = {"cost": cost, "gt_cost": gt_cost, "gap": gap, "runtime": timeit.default_timer() - start_time}
    return {k: v.item() if isinstance(v, torch.Tensor) and v.ndim == 0 else v for k, v in results.items()}


def create_timeout_error(iteration: int) -> TimeoutError:
    message = f"Process timed out for iteration {iteration}."
    return TimeoutError(message)


def create_no_result_error() -> RuntimeError:
    return RuntimeError("No result returned from the process.")


def create_process_error(error_message: str) -> RuntimeError:
    return RuntimeError(error_message)


def handle_timeout(process: mp.Process, iteration: int) -> None:
    if process.is_alive():
        process.terminate()
        raise create_timeout_error(iteration)


def handle_empty_queue(queue: mp.Queue) -> None:
    if queue.empty():
        raise create_no_result_error()


def handle_process_error(run_results: dict) -> None:
    if "error" in run_results:
        raise create_process_error(run_results["error"])


def process_iteration(config: Config, sample: tuple[Any, ...], queue: mp.Queue) -> None:
    """Run the single iteration and store the result in the queue."""
    try:
        result = run_single_iteration(config, sample)
        queue.put(result)
    except BaseException as e:  # noqa: BLE001 blind exception required
        queue.put({"error": str(e)})


def run_ea(config: Config) -> None:
    print(f"Running EA with config: {config}")
    dataset = dataset_factory(config)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=False)

    is_validation_run = config.validate_samples is not None
    if not is_validation_run:
        wandb.init(
            project=config.project_name,
            name=config.wandb_logger_name,
            entity=config.wandb_entity,
            config=config.__dict__,
            dir=config.logs_path,
        )

    results = []
    ctx = mp.get_context("spawn")

    for i, sample in tqdm(enumerate(dataloader)):
        queue = ctx.Queue()
        process = ctx.Process(target=process_iteration, args=(config, sample, queue))

        process.start()
        try:
            process.join(timeout=30 * 60)  # 30 minutes timeout
            handle_timeout(process, i)
            handle_empty_queue(queue)

            run_results = queue.get()
            handle_process_error(run_results)

            results.append(run_results)
            if not is_validation_run:
                wandb.log(run_results, step=i)
        except (TimeoutError, RuntimeError) as e:
            print(f"Error in iteration {i}: {e}")
        finally:
            if process.is_alive():
                process.terminate()
                process.join()

        if is_validation_run and i >= config.validate_samples - 1:
            break

    agg_results = {
        "avg_cost": np.mean([r["cost"] for r in results]),
        "avg_gt_cost": np.mean([r["gt_cost"] for r in results]),
        "avg_gap": np.mean([r["gap"] for r in results]),
        "avg_runtime": np.mean([r["runtime"] for r in results]),
        "n_evals": len(results),
    }

    if not is_validation_run:
        wandb.log(agg_results)
        agg_results["wandb_id"] = wandb.run.id

        table_saver = TableSaver(table_name="results/ea_results.csv")
        results_dict = get_results_dict(config, agg_results)
        table_saver.put(results_dict)

        wandb.finish()
