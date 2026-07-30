"""Regenerate the example input files, or make variants to test with.

    python example_input_files/make_example_input.py
    python example_input_files/make_example_input.py --n-per-group 20 --n-sites 3000
    python example_input_files/make_example_input.py --out my_test --group-names treated,untreated

The point of these files is that they are NOT the bundled cohort. Different
sample names, different column names, different group labels - so dropping them
into the studio exercises the whole ingest path the way your own data would.

The values are drawn from a distribution, not measured. A known signal is
planted in a fixed number of sites so a correct pipeline has something real to
find; if a run comes back with nothing, something is wrong with the run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def build(n_per_group=6, n_sites=800, n_signal=60, effect=0.35, seed=7,
          group_names=("case", "control"), id_prefixes=("CASE", "CTRL")):
    rng = np.random.default_rng(seed)

    sites = ["cg%08d" % i for i in rng.choice(90_000_000, n_sites, replace=False)]
    samples = ([f"{id_prefixes[0]}_{i:02d}" for i in range(1, n_per_group + 1)]
               + [f"{id_prefixes[1]}_{i:02d}" for i in range(1, n_per_group + 1)])

    # Beta values live on 0..1 and are roughly bimodal in real data; a beta
    # distribution is a reasonable stand-in for a test fixture.
    base = rng.beta(2, 2, size=n_sites)
    matrix = np.clip(
        np.stack([base + rng.normal(0, 0.05, n_sites) for _ in samples], axis=1),
        0.001, 0.999)

    # Plant the signal in the first group only.
    signal_rows = rng.choice(n_sites, min(n_signal, n_sites), replace=False)
    block = np.ix_(signal_rows, range(n_per_group))
    matrix[block] = np.clip(matrix[block] + effect, 0.001, 0.999)

    betas = pd.DataFrame(matrix, index=sites, columns=samples)
    betas.index.name = "probe"

    samples_table = pd.DataFrame({
        "sample_id": samples,
        "group": [group_names[0]] * n_per_group + [group_names[1]] * n_per_group,
        "age": rng.integers(40, 75, len(samples)),
    })
    return betas, samples_table, sorted(sites[i] for i in signal_rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-per-group", type=int, default=6)
    ap.add_argument("--n-sites", type=int, default=800)
    ap.add_argument("--n-signal", type=int, default=60,
                    help="how many sites carry a planted difference")
    ap.add_argument("--effect", type=float, default=0.35,
                    help="size of the planted difference, in beta units")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--group-names", default="case,control",
                    help="comma-separated; the second one is the reference group")
    ap.add_argument("--out", default=str(HERE), help="output directory")
    args = ap.parse_args()

    names = tuple(n.strip() for n in args.group_names.split(",", 1))
    prefixes = tuple(n.strip().upper()[:4] for n in names)

    betas, samples, planted = build(
        n_per_group=args.n_per_group, n_sites=args.n_sites, n_signal=args.n_signal,
        effect=args.effect, seed=args.seed, group_names=names, id_prefixes=prefixes)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    betas.to_csv(out / "methylation_data.tsv", sep="\t")
    samples.to_csv(out / "sample_list.tsv", sep="\t", index=False)
    (out / "planted_signal_sites.txt").write_text(
        "# Sites given a +%.2f difference in the '%s' group. A correct run should\n"
        "# recover most of these and little else.\n%s\n"
        % (args.effect, names[0], "\n".join(planted)), encoding="utf-8")

    print("wrote to %s" % out)
    print("  methylation_data.tsv    %s sites x %d samples" % (
        f"{len(betas):,}", len(betas.columns)))
    print("  sample_list.tsv         %d samples, %s vs %s" % (
        len(samples), names[0], names[1]))
    print("  planted_signal_sites.txt %d sites carry a real difference" % len(planted))


if __name__ == "__main__":
    main()
