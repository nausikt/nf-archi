process Ensemble {

    tag "consensus"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path label_files

    output:
    path "ensemble.parquet", emit: consensus
    path "coassoc.parquet",  emit: coassoc

    script:
    """
    ensemble.py \\
        --inputs ${label_files} \\
        --output ensemble.parquet \\
        --coassoc coassoc.parquet \\
        --threshold ${params.cluster.consensus_threshold}
    """
}
