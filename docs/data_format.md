# Data format

Required canonical fields: `date`, `item`, `category`, `price`, `unit_cost`, `units_sold` (cost may be supplied through a scenario). Optional POS transaction amount, status, discount amount, and discount percentage fields can be mapped in Data Setup. Refer to `src/config.py` and `src/data_pipeline/adapter.py` for the exact active mapping rules.

Data folders: `data/` is where the existing demo paths live; `data/synthetic/` is for small generated test fixtures; `data/private/`, `data/local/` and `data/uploads/` are git-ignored. The packaged project ZIP intentionally excludes CSV datasets and must be overlaid onto your existing repository to keep your local demo file.
