process AssignAnchors {

    tag "assign"

    conda     "${projectDir}/assets/env/cluster-ml.yml"
    container 'nf-archi-cluster-ml:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path embeddings
    path anchors
    path anchor_meta
    path ensemble

    output:
    path "prelabels.parquet",          emit: prelabels
    path "cluster_suggestions.json",   emit: cluster_suggestions

    script:
    """
    assign_anchors.py \\
        --embeddings ${embeddings} \\
        --anchors ${anchors} \\
        --anchor-meta ${anchor_meta} \\
        --ensemble ${ensemble} \\
        --top-k ${params.assign.top_k} \\
        --prelabels prelabels.parquet \\
        --cluster-suggestions cluster_suggestions.json
    """
}
