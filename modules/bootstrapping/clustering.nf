process Clustering {

    tag "${meta.sample_id}"

    input:
    tuple val(meta), val(record)

    output:
    tuple val(meta), val(record), env(cluster_id), emit: clustered

    script:
    """
    cat <<'NEXTFLOW_EOF'
Clustering running
  sample_id : ${meta.sample_id}
  batch     : ${meta.batch}
  question  : ${record.question}
NEXTFLOW_EOF

    export cluster_id="cluster_\$(shuf -i 1-5 -n 1)"
    echo "  cluster_id: \$cluster_id"
    """
}
