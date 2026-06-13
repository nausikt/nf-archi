include { validateParameters } from 'plugin/nf-schema'
include { LoadQueries        } from '../subworkflows/io/load_queries.nf'
include { CollectDataset } from '../subworkflows/io/collect_dataset.nf'
include { Embed } from '../modules/bootstrapping/embed.nf'
include { Clustering } from '../subworkflows/bootstrapping/clustering.nf'
include { Anchors } from '../subworkflows/bootstrapping/anchors.nf'
include { AssignAnchors } from '../modules/bootstrapping/assign_anchors.nf'

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

    Embed(CollectDataset.out.dataset.map { ds ->
        tuple(ds, 'embeddings.parquet', params.embed.text_fields.join(',')) })
    ch_embeddings = Embed.out.embeddings.first()

    Clustering(ch_embeddings, params.cluster.runs)

    // Optional pre-labeling overlay: rank user-prior anchors against each
    // sample (and each consensus cluster) for the expert's first pass.
    if( params.anchors?.categories || params.anchors?.tags || params.anchors?.flags ) {
        Anchors(params.outdir)
        AssignAnchors(
            ch_embeddings,
            Anchors.out.anchors.first(),
            Anchors.out.meta.first(),
            Clustering.out.consensus.first()
        )
    }
}
