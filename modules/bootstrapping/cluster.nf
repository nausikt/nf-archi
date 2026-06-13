import groovy.json.JsonOutput

process Cluster {

    tag "${run.name}"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping/clusters", mode: 'copy'

    input:
    val  run
    path embeddings

    output:
    path "cluster_${run.name}.parquet", emit: labels

    script:
    def run_json = JsonOutput.toJson(run)
    """
    cluster.py \\
        --input ${embeddings} \\
        --output cluster_${run.name}.parquet \\
        --run '${run_json}' \\
        --seed ${params.cluster.seed}
    """
}
