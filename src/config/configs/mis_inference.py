from config.config import Config

config = Config(
    task="mis",
    diffusion_type="gaussian",
    learning_rate=0.0002,
    weight_decay=0.0001,
    lr_scheduler="cosine-decay",
    data_path="data",
    test_split="mis/er_test",
    training_split="mis/er_test",
    validation_split="mis/er_test",
    training_split_label_dir=None,
    validation_split_label_dir=None,
    test_split_label_dir=None,
    models_path="models",
    ckpt_path="mis/mis_er_gaussian.ckpt",
    batch_size=4,
    num_epochs=50,
    diffusion_steps=1000,
    validation_examples=8,
    diffusion_schedule="linear",
    inference_schedule="cosine",
    inference_diffusion_steps=50,
    device="cuda",
    parallel_sampling=10,
    inference_trick="ddim",
    sparse_factor=-1,
    n_layers=12,
    hidden_dim=256,
    aggregation="sum",
    use_activation_checkpoint=True,
    fp16=False,
)
