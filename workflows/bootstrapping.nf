include { validateParameters } from 'plugin/nf-schema'
include { LoadQueries        } from '../subworkflows/io/load_queries.nf'
include { CollectDataset } from '../subworkflows/io/collect_dataset.nf'
include { Embed } from '../modules/bootstrapping/embed.nf'
include { Reduction } from '../subworkflows/bootstrapping/reduction.nf'
include { Clustering } from '../subworkflows/bootstrapping/clustering.nf'
include { Anchors } from '../subworkflows/bootstrapping/anchors.nf'
include { AssignAnchors } from '../modules/bootstrapping/assign_anchors.nf'
include { ArgillaExport } from '../modules/bootstrapping/argilla_export.nf'

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
    ch_dataset = CollectDataset.out.dataset.first()   // original text; reused by the Argilla export

    Embed(ch_dataset.map { ds ->
        tuple(ds, 'embeddings.parquet', params.embed.text_fields.join(',')) })
    ch_embeddings = Embed.out.embeddings.first()   // raw space (anchor comparisons)

    // PCA -> UMAP: clustering on the low-dim space fixes high-dim sparsity.
    // Gridable: each reduction variant x each clustering run = one ensemble
    // member; the primary variant supplies the geometry + viz (umap2) space.
    Reduction(Embed.out.embeddings)
    ch_umap2 = Reduction.out.umap2.first()    // viz space (anchor/sample placement)

    Clustering(Reduction.out.variants, Reduction.out.primary, params.cluster.runs)
    ch_consensus = Clustering.out.consensus.first()
    ch_reps      = Clustering.out.representatives.first()

    // Optional pre-labeling overlay: rank user-prior anchors against each
    // sample (and each consensus cluster) for the expert's first pass.
    if( params.anchors?.categories || params.anchors?.tags || params.anchors?.flags ) {
        Anchors(params.outdir)
        ch_anchor_meta = Anchors.out.meta.first()
        AssignAnchors(
            ch_embeddings,
            Anchors.out.anchors.first(),
            ch_anchor_meta,
            ch_consensus,
            ch_umap2
        )

        // Last hop: package the anchor-consensus prelabels for the representative
        // review queue and push them to the configured Argilla instance (opt-in).
        if( params.argilla?.enabled ) {
            ArgillaExport(
                ch_dataset,
                AssignAnchors.out.prelabels,
                ch_reps,
                ch_consensus,
                ch_anchor_meta
            )
        }
    }
}
