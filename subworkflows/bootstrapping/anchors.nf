import groovy.json.JsonOutput

include { Embed } from '../../modules/bootstrapping/embed.nf'

workflow Anchors {

    take:
    outdir            // value: publish root

    main:
    SchemaValidator.validate(params.anchors, 'schemas/anchors/taxonomy.json')

    // section name -> kind; flatten to canonical {id, kind, name, definition}
    def sections = [category: params.anchors.categories,
                    tag:      params.anchors.tags,
                    flag:     params.anchors.flags]
    def entries = sections.collectMany { kind, items ->
        (items ?: []).collect { it + [kind: kind] }
    }
    entries.each { SchemaValidator.validate(it, 'schemas/anchors/anchor.json') }
    assert entries*.id.unique().size() == entries.size() : "Duplicate anchor ids: ${entries*.id}"

    anchors_jsonl = Channel.fromList(entries)
        .map { a -> JsonOutput.toJson([sample_id: a.id, name: a.name, definition: a.definition]) }
        .collectFile(name: 'anchors.jsonl', newLine: true, sort: true)

    meta = Channel.fromList(entries)
        .map { a -> JsonOutput.toJson([id: a.id, kind: a.kind, name: a.name]) }
        .collectFile(name: 'anchors_meta.jsonl', newLine: true, sort: true,
                     storeDir: "${outdir}/bootstrapping")

    Embed(anchors_jsonl.map { f -> tuple(f, 'anchors.parquet', params.anchors.text_fields.join(',')) })

    emit:
    anchors = Embed.out.embeddings
    meta    = meta
}