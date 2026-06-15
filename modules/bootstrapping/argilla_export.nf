process ArgillaExport {

    tag "argilla"

    conda "${projectDir}/assets/env/argilla.yml"

    publishDir "${params.outdir}/bootstrapping", mode: 'copy'

    // Bring-your-own Argilla: $ARGILLA_API_URL / $ARGILLA_API_KEY are read from the
    // launch environment by the script (the key never appears on the command line).

    input:
    path dataset
    path prelabels
    path representatives
    path ensemble
    path anchor_meta

    output:
    path "argilla_export.json", emit: summary

    script:
    def api_url   = params.argilla.api_url ? "--api-url ${params.argilla.api_url}" : ''
    def overwrite = params.argilla.overwrite ? '--overwrite' : ''
    def dry       = params.argilla.dry_run  ? '--dry-run'    : ''
    """
    argilla_export.py \\
        --dataset ${dataset} \\
        --prelabels ${prelabels} \\
        --representatives ${representatives} \\
        --ensemble ${ensemble} \\
        --anchor-meta ${anchor_meta} \\
        --scope ${params.argilla.scope} \\
        --top-k-tags ${params.argilla.top_k_tags} \\
        --workspace ${params.argilla.workspace} \\
        --version ${params.argilla.version} \\
        ${api_url} ${overwrite} ${dry} \\
        --output argilla_export.json
    """
}
