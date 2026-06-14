include { Cluster }         from '../../modules/bootstrapping/cluster.nf'
include { Ensemble }        from '../../modules/bootstrapping/ensemble.nf'
include { Representatives } from '../../modules/bootstrapping/representatives.nf'

workflow Clustering {

    take:
    variants          // channel of tuple(reduction_name, reduced_file) — one or many
    primary           // value: primary reduced file (representatives geometry)
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

    // Cartesian: every clustering run on every reduction variant becomes one
    // ensemble member, named <reduction>__<cluster>. Evidence accumulation then
    // makes the consensus robust to the reduction choice too.
    ch_members = Channel.fromList(runs)
        .combine(variants)
        .map { run, rname, rfile ->
            tuple(run + [ name: "${rname}__${run.name}".toString() ], rfile) }

    Cluster(ch_members)

    // Deterministic order into Ensemble: collect() emits in task-completion
    // order (nondeterministic), which would change the staged file list and
    // thrash Ensemble's cache on every -resume. toSortedList() pins the order
    // so Ensemble caches whenever its inputs/params are unchanged.
    Ensemble(Cluster.out.labels.toSortedList(), Cluster.out.metrics.toSortedList())
    Representatives(primary, Ensemble.out.consensus)

    // per-member quality metrics -> one JSONL artifact (raw inputs to weighting)
    ch_member_metrics = Cluster.out.metrics
        .collectFile(name: 'member_metrics.jsonl', newLine: true, sort: true,
                     storeDir: "${params.outdir}/bootstrapping")

    emit:
    labels          = Cluster.out.labels
    consensus       = Ensemble.out.consensus
    coassoc         = Ensemble.out.coassoc
    weights         = Ensemble.out.weights
    representatives = Representatives.out.representatives
    member_metrics  = ch_member_metrics
}