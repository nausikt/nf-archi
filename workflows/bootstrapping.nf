include { validateParameters } from 'plugin/nf-schema'
include { LoadQueries        } from '../subworkflows/io/load_queries.nf'
include { CollectDataset } from '../subworkflows/io/collect_dataset.nf'

workflow BootstrappingDataset {

    main:
    validateParameters()

    // Native Nextflow glob — file, directory glob, or recursive
    ch_files = Channel.fromPath(
        PathUtils.resolveInputPattern(params.input),
        checkIfExists: true
    )

    LoadQueries(
        ch_files,
        'schemas/inputs/raw_archi_query_format_extended.json',
        params.workflow
    )

    // LoadQueries.out.records.view { meta, record ->
    //     "▶  [${meta.sample_id}] ${meta.batch} — ${record.question}"
    // }

    CollectDataset(LoadQueries.out.records, params.outdir)
}
