// One reduction recipe -> one clustering-space artifact (an ensemble axis).
process Reduce {

    tag "${spec.name}"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping/reduced", mode: 'copy'

    input:
    val  spec
    path embeddings

    output:
    tuple val(spec.name), path("reduced_${spec.name}.parquet"), emit: reduced

    script:
    """
    reduce.py \\
        --input ${embeddings} \\
        --reduced reduced_${spec.name}.parquet \\
        --pca-components ${spec.pca_components} \\
        --n-components ${spec.n_components} \\
        --n-neighbors ${spec.n_neighbors} \\
        --min-dist ${spec.min_dist} \\
        --seed ${params.reduce.seed}
    """
}

// Viz space (2D) for the dashboard — built once, from the primary reduction.
process ReduceViz {

    tag "viz"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    val  spec
    path embeddings

    output:
    path "umap2.parquet", emit: umap2

    script:
    """
    reduce.py \\
        --input ${embeddings} \\
        --umap2 umap2.parquet \\
        --pca-components ${spec.pca_components} \\
        --viz-n-neighbors ${params.reduce.viz.n_neighbors} \\
        --viz-min-dist ${params.reduce.viz.min_dist} \\
        --seed ${params.reduce.seed}
    """
}
