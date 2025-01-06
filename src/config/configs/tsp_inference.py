from config.myconfig import Config

config = Config(
    task="tsp",
    diffusion_type="categorical",
    learning_rate=0.0002,
    weight_decay=0.0001,
    lr_scheduler="cosine-decay",
    data_path="data",
    models_path="models",
    batch_size=32,
    num_epochs=50,
    diffusion_steps=50,
    inference_diffusion_steps=50,
    diffusion_schedule="linear",
    inference_schedule="cosine",
    device="cuda",
    sparse_factor=-1,
    n_layers=12,
    hidden_dim=256,
    aggregation="sum",
    use_activation_checkpoint=False,
    fp16=False,
    test_split_label_dir=None,
    training_split_label_dir=None,
    validation_split_label_dir=None,
)
