import groovy.json.JsonOutput

include { validateParameters } from 'plugin/nf-schema'
include { LoadQueries        } from '../subworkflows/io/load_queries.nf'
include { CollectDataset } from '../subworkflows/io/collect_dataset.nf'
include { Embed } from '../modules/bootstrapping/embed.nf'
include { MergeEmbeddings } from '../modules/bootstrapping/merge_embeddings.nf'
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
    ch_dataset = CollectDataset.out.dataset

    // Embed per input batch (one chunk per month) in parallel, capped at
    // params.embed.max_forks, then fold the shards back into one parquet. This
    // keeps each chunk independently -resume-cacheable and the endpoint trackable.
    ch_chunks = LoadQueries.out.records
        .map { meta, record ->
            def canonical = [sample_id: meta.sample_id, workflow: meta.workflow, batch: meta.batch] + record
            tuple(meta.batch, JsonOutput.toJson(canonical) + '\n')
        }
        .collectFile(sort: true) { batch, line -> [ batch, line ] }

    Embed(ch_chunks.map { chunk ->
        tuple(chunk, "embeddings.${chunk.baseName}.parquet", params.embed.text_fields.join(',')) })

    MergeEmbeddings(Embed.out.embeddings.collect())
    ch_embeddings = MergeEmbeddings.out.embeddings

    // PCA -> UMAP: clustering on the low-dim space fixes high-dim sparsity.
    // Gridable: each reduction variant x each clustering run = one ensemble
    // member; the primary variant supplies the geometry + viz (umap2) space.
    Reduction(MergeEmbeddings.out.embeddings)
    ch_umap2 = Reduction.out.umap2

    Clustering(Reduction.out.variants, Reduction.out.primary, params.cluster.runs)
    ch_consensus = Clustering.out.consensus
    ch_reps      = Clustering.out.representatives

    // Optional pre-labeling overlay: rank user-prior anchors against each
    // sample (and each consensus cluster) for the expert's first pass.
    if( params.anchors?.categories || params.anchors?.tags || params.anchors?.flags ) {
        Anchors(params.outdir)
        ch_anchor_meta = Anchors.out.meta
        AssignAnchors(
            ch_embeddings,
            Anchors.out.anchors,
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
