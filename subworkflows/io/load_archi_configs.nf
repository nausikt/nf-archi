
workflow LoadArchiConfigs {

    take:
    ch_dirs           // channel of directory paths
    workflow_name     // value: workflow identifier

    main:
    configs = ch_dirs
        .map { dir ->
            def meta = [
                config_id : dir.name,
                workflow  : workflow_name,
                source    : dir.toString()
            ]
            return [meta, dir]
        }

    emit:
    configs
}
