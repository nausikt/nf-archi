process Reduce {

    tag "reduce"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path embeddings

    output:
    path "reduced.parquet", emit: reduced
    path "umap3.parquet",   emit: umap3

    script:
    """
    reduce.py \\
        --input ${embeddings} \\
        --reduced reduced.parquet \\
        --umap3 umap3.parquet \\
        --pca-components ${params.reduce.pca_components} \\
        --n-components ${params.reduce.n_components} \\
        --n-neighbors ${params.reduce.n_neighbors} \\
        --min-dist ${params.reduce.min_dist} \\
        --viz-n-neighbors ${params.reduce.viz.n_neighbors} \\
        --viz-min-dist ${params.reduce.viz.min_dist} \\
        --seed ${params.reduce.seed}
    """
}
