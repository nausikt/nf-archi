import groovy.json.JsonOutput

process Cluster {

    tag "${run.name}"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping/clusters", mode: 'copy'

    input:
    tuple val(run), path(embeddings)

    output:
    path "cluster_${run.name}.parquet", emit: labels
    path "metrics_${run.name}.json",    emit: metrics

    script:
    def run_json = JsonOutput.toJson(run)
    """
    cluster.py \\
        --input ${embeddings} \\
        --output cluster_${run.name}.parquet \\
        --metrics metrics_${run.name}.json \\
        --run '${run_json}' \\
        --space ${params.cluster.metric_space} \\
        --seed ${params.cluster.seed}
    """
}
