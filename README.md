## nf-archi
*A Reproducible and Scalable Workflow for Dataset Creation, Benchmarking, and Operational Phase-Space Analysis in Archi*

<img width="2550" height="1288" alt="Screenshot 2026-06-15 at 14 06 35" src="https://github.com/user-attachments/assets/54f76bcd-e42a-488f-87c6-b705feef17f1" />

```bash
❯ nextflow run . --help
Nextflow 26.04.4 is available - Please consider updating your version to it

 N E X T F L O W   ~  version 25.10.4

Launching `./main.nf` [nauseous_laplace] DSL2 - revision: 41e86c5579

--help              [boolean, string] Show the help message for all top level parameters. When a parameter is given to `--help`, the full
help message of that parameter will be printed.
--helpFull          [boolean]         Show the help message for all non-hidden parameters.
--showHidden        [boolean]         Show all hidden parameters in the help message. This needs to be used in combination with `--help`
or `--helpFull`.

Common
  --outdir          [string] Directory for pipeline outputs [default: results]
  --workflow        [string] Which workflow to run  (accepted: benchmarking, bootstrapping, prelabelling)

Bootstrapping
  --input           [string] Path or glob to query files (.json or .jsonl)
  --embed           [object] Embedding settings (Ollama) (This parameter has sub-parameters. Use '--help embed' to see
all sub-parameters)
  --reduce          [object] Dimensionality reduction (PCA -> UMAP) before clustering (This parameter has
sub-parameters. Use '--help reduce' to see all sub-parameters)
  --cluster         [object] Clustering ensemble settings (This parameter has sub-parameters. Use '--help cluster' to
see all sub-parameters)
  --ensemble        [object] Weighted evidence-accumulation consensus (semi-automatic) (This parameter has
sub-parameters. Use '--help ensemble' to see all sub-parameters)
  --anchors         [object] Pre-labeling anchors (user priors embedded into the data space). Provide via -params-file;
deep-validated against schemas/anchors/taxonomy.json (This parameter has sub-parameters.
Use '--help anchors' to see all sub-parameters)
  --assign          [object] Anchor assignment settings (This parameter has sub-parameters. Use '--help assign' to see
all sub-parameters)
  --representatives [object] Per-cluster representative sampling for expert review (This parameter has sub-parameters.
Use '--help representatives' to see all sub-parameters)
  --argilla         [object] Argilla export of prelabels + representatives as a review queue (opt-in; bring-your-own instance,
api key via $ARGILLA_API_KEY) (This parameter has sub-parameters. Use '--help argilla' to
see all sub-parameters)

Benchmarking
  --queries         [string] Path or glob to query files
  --configs         [string] Path to directory containing archi configs

------------------------------------------------------
```
