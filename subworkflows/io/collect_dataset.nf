import groovy.json.JsonOutput

workflow CollectDataset {

    take:
    ch_records        // queue of [meta, record]
    outdir            // value: publish root

    main:
    dataset = ch_records
        .map { meta, record ->
            def canonical = [
                sample_id : meta.sample_id,
                workflow  : meta.workflow,
                batch     : meta.batch,
            ] + record
            JsonOutput.toJson(canonical)
        }
        .collectFile(
            name:     'dataset.jsonl',
            newLine:  true,
            sort:     true,
            storeDir: "${outdir}/bootstrapping"
        )

    emit:
    dataset           // single-item channel: path to dataset.jsonl
}
