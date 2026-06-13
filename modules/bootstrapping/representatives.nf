process Representatives {

    tag "representatives"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path embeddings
    path ensemble

    output:
    path "representatives.parquet", emit: representatives

    script:
    """
    representatives.py \\
        --embeddings ${embeddings} \\
        --ensemble ${ensemble} \\
        --output representatives.parquet \\
        --n-medoid ${params.representatives.n_medoid} \\
        --n-boundary ${params.representatives.n_boundary} \\
        --n-outlier ${params.representatives.n_outlier}
    """
}
