import numpy as np
import pandas as pd

from scipy import stats


def params(scenario, fleet_size=1000, seed=0):
    
    hyperpriors = {}
    keys = pd.DataFrame([key.split('_') for key in scenario.keys()]).set_index(0)
    
    params = pd.DataFrame(columns=list(set([key.split('_')[0] for key in scenario.keys()])), 
                          index=range(fleet_size))
        
    for p in params.keys():
        distribution_name = scenario[p+'_distribution']
        if pd.isnull(distribution_name):
            continue
            
        sampling_distribution = getattr(stats, distribution_name)
        
        hyperparams = eval(scenario[p+'_hyperparams'])
        sampling_distribution = sampling_distribution(*hyperparams)

        params[p] = sampling_distribution.rvs(size=fleet_size, random_state=seed)
        params[p] = params[p].round(4)

    return params


def failure_data(params, X, link, seed=0, fleet_size=1000):
    # remove null parameters
    for p in params.keys():
        if pd.isnull(params[p].loc[0]):
            params = params.drop(p, axis=1)
            
    n_components = params.groupby(params.keys().tolist())['constant'].count()
    
    p_labels = params.keys()
    params = params.set_index(params.keys().tolist())
    
    
    # note that for a Poisson process Y where Y is the sum of Poisson processes...
    #        Y = Y_1 + Y_2 + Y_3 + Y_4
    # The rate l is also the sum of the rates
    #        l = l_1 + l_2 + l_3 + l_4
    # So the failure rate for the system overall is just the sum of the failure rates
    # for the individual components
    failure_rate = pd.Series(0, index=X.index)
    for p_vals in params.index.unique():
        component_failure_rate = pd.Series(link().failure_rate(dict(zip(p_labels, p_vals)), X), index=X.index)
        failure_rate += n_components.loc[p_vals] * component_failure_rate

    failure_realization = pd.Series(index=X.index)

    for rate in failure_rate.drop_duplicates():
        idx = failure_rate == rate
        failure_realization.loc[idx] = stats.poisson.rvs(rate, size=sum(idx), random_state=seed)

    failure_realization.loc[failure_realization>fleet_size] = fleet_size
    return failure_realization, failure_rate