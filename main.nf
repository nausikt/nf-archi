include { BootstrappingDataset } from './workflows/bootstrapping.nf'

workflow {
    switch (params.workflow) {
        case 'bootstrapping':
            BootstrappingDataset(); break
        default:
            error "Unknown workflow: ${params.workflow}. Choose: bootstrapping"
    }
}
