import groovy.json.JsonOutput

process Ensemble {

    tag "consensus"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path label_files
    path metric_files

    output:
    path "ensemble.parquet",     emit: consensus
    path "coassoc.parquet",      emit: coassoc
    path "member_weights.json",  emit: weights

    script:
    // Canonical (key-sorted) JSON so re-ordering the override map does NOT
    // change the script text -> no spurious cache miss. Editing an actual
    // weight DOES change it -> Ensemble (and only Ensemble onward) recomputes.
    def mw = params.ensemble.member_weights
    def overrides = JsonOutput.toJson((mw instanceof Map ? mw : [:]).sort())
    """
    ensemble.py \\
        --inputs ${label_files} \\
        --metrics ${metric_files} \\
        --output ensemble.parquet \\
        --coassoc coassoc.parquet \\
        --weights member_weights.json \\
        --threshold ${params.ensemble.threshold} \\
        --weight-mode ${params.ensemble.weight} \\
        --min-clusters ${params.ensemble.auto.min_clusters} \\
        --max-noise ${params.ensemble.auto.max_noise} \\
        --max-dominance ${params.ensemble.auto.max_dominance} \\
        --overrides '${overrides}'
    """
}
