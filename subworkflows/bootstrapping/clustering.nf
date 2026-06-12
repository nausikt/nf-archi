include { Cluster } from '../../modules/bootstrapping/cluster.nf'

workflow Clustering {

    take:
    embeddings        // single-item channel: embeddings.parquet
    runs_file         // value: path to runs.json

    main:
    ch_runs = Channel.fromList( JsonReader.read(file(runs_file)) )   // queue: one map per run
    ch_emb  = embeddings.first()                                     // value: reused by every run

    Cluster(ch_runs, ch_emb)

    emit:
    labels = Cluster.out.labels      // queue: one labels parquet per run
}
