include { Cluster } from '../../modules/bootstrapping/cluster.nf'

workflow Clustering {

    take:
    embeddings        // single-item channel: embeddings.parquet
    runs_file         // value: path to runs.json (fallback when no grid)

    main:
    def ABBR = [min_cluster_size:'mcs', min_samples:'ms', n_clusters:'k',
                linkage:'lk', metric:'m', distance_threshold:'dt']

    def runs = params.cluster.grid
        ? Grid.expandGroups(params.cluster.grid, 'algorithm').collect { spec ->
              spec + [ name: "${spec.algorithm}_${Grid.slug(spec, ABBR, ['algorithm'])}".toString() ] }
        : JsonReader.read(file(runs_file))

    if( params.cluster.grid )
        SchemaValidator.validate(params.cluster.grid, 'schemas/cluster/grid.json')
    runs.each { SchemaValidator.validate(it, 'schemas/cluster/run.json') }
    assert runs*.name.unique().size() == runs.size() : "Duplicate run names: ${runs*.name}"

    ch_runs = Channel.fromList(runs)
    ch_emb  = embeddings.first()

    Cluster(ch_runs, ch_emb)

    emit:
    labels = Cluster.out.labels
}