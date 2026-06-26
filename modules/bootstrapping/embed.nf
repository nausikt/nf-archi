
process Embed {

    tag "${out_name}"

    errorStrategy 'retry'
    maxRetries 3

    // cap concurrent inferencing so the endpoint stays trackable / unsaturated
    maxForks params.embed.max_forks

    conda     "${projectDir}/assets/env/embed.yml"
    container 'nf-archi-embed:0.1.0'

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    input:
    tuple path(records), val(out_name), val(text_fields)

    output:
    path out_name, emit: embeddings

    script:
    """
    embed.py \\
        --input ${records} \\
        --output ${out_name} \\
        --endpoint ${params.embed.endpoint} \\
        --model ${params.embed.model} \\
        --text-fields ${text_fields} \\
        --batch-size ${params.embed.batch_size}
    """
}
