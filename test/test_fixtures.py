
def test_minimal_test_esM(minimal_test_esM):

    # TODO: add test with time series aggregation ?
    # minimal_test_esM.cluster(numberOfTypicalPeriods=2)

    minimal_test_esM.optimize(timeSeriesAggregation=False, solver = 'glpk')


def test_multi_node_test_esM_init(multi_node_test_esM_init):

    multi_node_test_esM_init.cluster(numberOfTypicalPeriods=3)

    multi_node_test_esM_init.optimize(timeSeriesAggregation=True, solver = 'glpk')

