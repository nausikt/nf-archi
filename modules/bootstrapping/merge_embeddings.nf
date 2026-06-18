process MergeEmbeddings {

    tag "merge"

    conda     "${projectDir}/assets/env/embed.yml"
    container 'nf-archi-embed:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path shards

    output:
    path "embeddings.parquet", emit: embeddings

    script:
    """
    merge_parquet.py --inputs ${shards} --output embeddings.parquet --sort-by sample_id
    """
}
