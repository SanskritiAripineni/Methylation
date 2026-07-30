# Example input files — for testing the studio with "your own" data

Drag `methylation_data.tsv` and `sample_list.tsv` onto the drop zone in
Methylation Studio (step 1, "Your own files"). They are deliberately **not** the
bundled cohort: different sample names, different column names, different group
labels. Dropping them exercises the same path your real data would take.

| file | what it is |
|---|---|
| `methylation_data.tsv` | 800 DNA sites × 12 samples of beta values. Sites are rows, samples are columns. |
| `sample_list.tsv` | 12 samples in two groups — `case` (6) and `control` (6) — plus an age column. |
| `planted_signal_sites.txt` | The 60 sites given a real, known difference. A correct run should find most of these and little else. |
| `make_example_input.py` | Regenerates the two files, or makes bigger/smaller variants. |

## What you should see

On drop, the studio reads the files and reports what it found — without being
told, because it works it out from the contents rather than the filenames:

```
Methylation data   methylation_data.tsv   800 sites across 12 samples.
Sample list        sample_list.tsv        12 samples, grouped by 'group'.

Ready to run. No site information file, so results will not carry gene names.
Comparing case against control. A positive difference means more methylation
in case.  (matched the word 'control')
Reading sample_id as the sample name and group as the group.
```

Then **Quick test run** finishes in seconds, and **Full analysis** finds roughly
60 changed sites — the ones that were planted. Around 56 survive the effect-size
filter at the Standard preset.

Two things are expected and not faults:

- **No gene names.** There is no site-information file, so every site is labelled
  "unclear" for the switched-off / switched-on call, and pathway enrichment finds
  nothing. The screen says so.
- **A perfect prediction score.** With 12 samples and a planted signal, the
  classifier separates the groups completely. That is what a fixture with an
  obvious answer looks like, not evidence the method is that good.

## Making variants

```bash
python example_input_files/make_example_input.py --n-per-group 20 --n-sites 3000
python example_input_files/make_example_input.py --group-names treated,untreated --out my_test
python example_input_files/make_example_input.py --n-signal 0        # nothing to find
```

`--n-signal 0` is the useful negative control: a correct pipeline should come
back with **nothing significant**, and if it reports hits anyway, something is
wrong. Note that the second `--group-names` value is treated as the reference
group, and the sign of every difference depends on that.

## Using your own real files

Same two files, same shape:

- **Methylation table** — sites as rows, samples as columns, tab-separated
  (`.tsv` or `.tsv.gz`). Beta values between 0 and 1. First column is the site id.
- **Sample list** — one row per sample. A column of sample names that match the
  table's column headers, and a column with exactly **two** groups. The column
  names themselves do not matter; the studio finds them.
- **Site information** — optional. `probe_id`, `gene`, `chrom` and a region
  column gets you gene names, promoter context and pathways.

Under 100 MB through the browser. Note the pipeline starts from **beta values**,
not raw IDAT files — turning IDATs into betas is a separate upstream step it does
not do.
