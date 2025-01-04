from __future__ import annotations

import pytest
from config.configs.mis_inference import config as mis_inference_config
from config.configs.tsp_inference import config as tsp_inference_config
from config.myconfig import Config

from difusco.difusco_initialization_experiments import run_difusco_initialization_experiments


@pytest.fixture
def config_factory() -> Config:
    def _config_factory(task: str) -> Config:
        common = Config(
            data_path="data",
            logs_path="logs",
            results_path="results",
            models_path="models",
            pop_size=2,
            parallel_sampling=2,
            sequential_sampling=1,
            diffusion_steps=2,
            inference_diffusion_steps=50,
            validate_samples=2,
            wandb_logger_name="justatest",
            np_eval=True,
        )
        if task == "mis":
            config = Config(
                task="mis",
                test_split="mis/er_50_100/test",
                test_split_label_dir="mis/er_50_100/test_labels",
                training_split="mis/er_50_100/train",
                training_split_label_dir="mis/er_50_100/train_labels",
                validation_split="mis/er_50_100/test",
                validation_split_label_dir="mis/er_50_100/test_labels",
                ckpt_path="mis/mis_er_50_100_gaussian.ckpt",
            )
            config = common.update(config)
            return mis_inference_config.update(config)
        if task == "tsp":
            config = Config(
                task="tsp",
                test_split="tsp/tsp50_test_concorde.txt",
                training_split="tsp/tsp50_train_concorde.txt",
                validation_split="tsp/tsp50_test_concorde.txt",
                ckpt_path="tsp/tsp50_categorical.ckpt",
            )
            config = common.update(config)
            return tsp_inference_config.update(config)

        raise ValueError(f"Invalid task: {task}")

    return _config_factory


@pytest.mark.parametrize("task", ["mis", "tsp"])
def test_difusco_initialization_experiments(config_factory: Config, task: str) -> None:
    config = config_factory(task)
    run_difusco_initialization_experiments(config)
