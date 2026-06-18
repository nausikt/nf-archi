include { Reduce }    from '../../modules/bootstrapping/reduce.nf'
include { ReduceViz } from '../../modules/bootstrapping/reduce.nf'

workflow Reduction {

    take:
    embeddings        // single-item channel: embeddings.parquet (raw space)

    main:
    def ABBR = [pca_components:'pca', n_components:'n', n_neighbors:'nn', min_dist:'md']

    // scalar params are the defaults; the grid only needs to vary the axes you care
    // about (unspecified axes fall back to these).
    def defaults = [pca_components: params.reduce.pca_components,
                    n_components:   params.reduce.n_components,
                    n_neighbors:    params.reduce.n_neighbors,
                    min_dist:       params.reduce.min_dist]

    def runs = params.reduce.grid
        ? Grid.product(params.reduce.grid).collect { spec ->
              def merged = defaults + spec
              merged + [ name: Grid.slug(merged, ABBR) ] }
        : [ defaults + [ name: 'primary' ] ]

    if( params.reduce.grid )
        SchemaValidator.validate(params.reduce.grid, 'schemas/reduce/grid.json')
    runs.each { SchemaValidator.validate(it, 'schemas/reduce/run.json') }
    assert runs*.name.unique().size() == runs.size() : "Duplicate reduction names: ${runs*.name}"

    // each recipe -> a clustering-space variant (tuple: name, file)
    Reduce(Channel.fromList(runs), embeddings)

    // primary = first recipe: supplies the single viz space + representatives geometry
    def primarySpec = runs[0]
    ReduceViz(primarySpec, embeddings)

    ch_primary = Reduce.out.reduced
        .filter { name, _f -> name == primarySpec.name }
        .map    { _name, f -> f }

    emit:
    variants = Reduce.out.reduced     // tuple(name, reduced_file) — one or many
    primary  = ch_primary             // value: primary reduced file (geometry)
    umap2    = ReduceViz.out.umap2
}
