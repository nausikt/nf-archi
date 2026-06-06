
workflow LoadQueries {

    take:
    ch_files          // channel of file paths (queue)
    schema_path       // value: JSON Schema file path
    workflow_name     // value: workflow identifier

    main:
    records = ch_files
        .flatMap { file ->
            JsonReader.read(file).collect { record -> [file.name, record] }
        }
        .filter  { batch, record -> record instanceof Map && record.question }
        .map     { batch, record ->
            SchemaValidator.validate(record, schema_path)
            def meta = [
                sample_id : MetaUtils.stableId(record),
                workflow  : workflow_name,
                batch     : batch
            ]
            return [meta, record]
        }

    emit:
    records
}

