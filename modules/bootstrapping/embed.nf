
process Embed {

    tag "embed"

    conda     "${projectDir}/assets/env/embed.yml"
    container 'nf-archi-embed:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    path dataset

    output:
    path 'embeddings.parquet', emit: embeddings

    script:
    """
    embed.py \\
        --input ${dataset} \\
        --output embeddings.parquet \\
        --endpoint ${params.embed.endpoint} \\
        --model ${params.embed.model} \\
        --text-fields ${params.embed.text_fields.join(',')} \\
        --batch-size ${params.embed.batch_size}
    """
}
