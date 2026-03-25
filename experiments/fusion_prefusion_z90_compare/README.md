# Fusion Pre-Zscore Experiment

This experiment compares two fusion methods built from the same selected constituents:

- `fusion_plain`: sign-align and lag-align each constituent, then average directly
- `fusion_pre_z90`: sign-align and lag-align each constituent, apply 90-day rolling z-score to each constituent, then average

The second method should match the current official pipeline in `factor_build/04_fusion_by_rules_and_corr_direction.ipynb`.

Run:

```bash
python experiments/fusion_prefusion_z90_compare/run_experiment.py
```

Outputs are written to:

```text
experiments/fusion_prefusion_z90_compare/outputs/
```
