# DIFUSCO

This repository contains the code of my Master Thesis, which is based on the work of [Difusco - Sun et al. (2023)](https://arxiv.org/abs/2302.08224).

-----

## Table of Contents

- [Dependencies](#dependencies)
- [Data](#data)
  - [Traveling Salesman Problem](#traveling-salesman-problem)
- [Models](#models)
- [License](#license)

## Dependencies and Installation

This project uses [hatch](https://hatch.pypa.io/) as a project manager. To install it, just `pip install hatch`. 

Unfortunately, two dependencies (`torch-scatter` and `torch-sparse`) require `torch` as an runtime dependency. The usual `hatch` dependency sync will not work for these two packages. To install them, do:

```bash

hatch shell # to create and enter the environment

pip install torch-scatter torch-sparse -f https://pytorch-geometric.com/whl/torch-2.3.1+cu121.html

```
You only need to install `torch-scatter`, `torch-sparse` once. After that, you can use `hatch run` as usual to run the project, and dependencies will sync automatically (without removing the extra installed packages).

Generating the data for the TSP instances requires the `lkh` solver, which is run via the python wrapper `lkh`. To install it, use the [official LKH-3 site](
http://akira.ruc.dk/~keld/research/LKH-3/). Make sure to specify the ``--lkh_path`` argument pointing to the LKH-3 binary when generating the data with this solver.

Finally, we need to compile the `cython` code for the TSP heuristics. To do so, run the following command:

```bash
cd src/difusco/tsp/cython_merge
python setup.py build_ext --inplace
```


## CLI Usage

There is a simple click CLI that can be used to run all the relevant modules. To see the available commands, run:

```bash
hatch run cli --help
```

There are two groups of commands: `difusco` and `ea`. Run `hatch run cli difusco --help` and `hatch run cli ea --help` to see the available commands for each group.


## Data

The data should be saved following the directory structure:

```bash
difusco/
├── data/                      # Directory for datasets
│   ├── tsp/                   # TSP dataset files
│   │   ├── tsp500_train_concorde.txt  # Training data for TSP
│   │   ├── tsp1000_train_concorde.txt # Additional training data for TSP
│   │   └── ...                # Other TSP data files
│   ├── mis/                   # MIS dataset files
│   │   ├── er_50_100/         # ER-50-100 dataset
│   │   ├── er_700_800/        # ER-700-800 dataset
│   │   ├── satlib/            # SATLIB dataset
│   │   └── ...                # Other MIS data files
│   └── etc/                   # Other datasets or resources
│       ├── example_data.txt    # Example dataset
│       └── ...                # Other miscellaneous data files
```
### Traveling Salesman Problem

The data for the TSP comes from different sources. 
 - Files tsp{50,100}_{test,train}_concorde.txt come from [chaitjo/learning-tsp](https://github.com/chaitjo/learning-tsp) (Resources section).
 - Files tsp{500,1000,10000}_test_concorde.txt come from [Spider-scnu/TSP](https://github.com/Spider-scnu/TSP) (Dataset section).
 - Files tsp{500,1000,10000}_train_concorde.txt are generated using the following commands:

```bash
hatch run difusco generate_tsp_data \
  --min_nodes 500 \
  --max_nodes 500 \
  --num_samples 128000 \
  --batch_size 128 \
  --filename "/data/tsp/tsp500_train_concorde.txt" \
  --seed 1234 \
  --lkh_path "/path/to/lkh"
```

```bash
hatch run difusco generate_tsp_data \
  --min_nodes 1000 \
  --max_nodes 1000 \
  --num_samples 64000 \
  --batch_size 128 \
  --filename "/data/tsp/tsp1000_train_concorde.txt" \
  --seed 1234 \
  --lkh_path "/path/to/lkh"
```

```bash
hatch run difusco generate_tsp_data \
  --min_nodes 10000 \
  --max_nodes 10000 \
  --num_samples 64000 \
  --batch_size 65 \
  --filename "/data/tsp/tsp10000_train_concorde.txt" \
  --seed 1234 \
  --lkh_path "/path/to/lkh"
```
## Models

Trained models by the work of [Difusco - Sun et al. (2023)](https://github.com/Edward-Sun/DIFUSCO) can be found here: [Difusco Models](https://drive.google.com/drive/folders/1IjaWtkqTAs7lwtFZ24lTRspE0h1N6sBH).

We recommend saving the models in the following directory structure:

```bash
difusco/
├── models/                    # Directory for models
│   ├── tsp/                   # TSP models
│   ├── mis/                   # MIS models
│   └── etc/                   # Other models
```

## License

`difusco` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
