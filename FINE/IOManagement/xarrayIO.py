import time
from pathlib import Path
from typing import Dict
from contextlib import contextmanager

import pandas as pd
import xarray as xr
from netCDF4 import Dataset

import FINE.utils as utils
from FINE.IOManagement import dictIO, utilsIO
from FINE.IOManagement.utilsIO import processXarrayAttributes

def close_dss(dss):
    if isinstance(dss, dict):
        for value in dss.values():
            if isinstance(value, dict):
                close_dss(value)
            elif isinstance(value, xr.Dataset):
                value.close()
            else:
                pass
    elif isinstance(dss, xr.Dataset):
        dss.close()

@contextmanager
def esm_input_to_datasets(esM):  
    """Takes esM instance and converts it into an xarray dataset. Optionally, the 
    dataset can be saved as a netcdf file.
    
    :param esM: EnergySystemModel instance in which the optimized model is held
    :type esM: EnergySystemModel instance

    :param save: indicates if the created xarray dataset should be saved
        |br| * the default value is False
    :type save: boolean

    :param file_name: output file name (can include full path)
        |br| * the default value is 'esM_instance.nc4'
    :type file_name: string
 
    :return: xr_ds - esM instance data in xarray dataset format 
    """
    
    #STEP 1. Get the esm and component dicts 
    esm_dict, component_dict = dictIO.exportToDict(esM)

    #STEP 2. Get the iteration dicts 
    df_iteration_dict, series_iteration_dict, constants_iteration_dict = \
        utilsIO.generateIterationDicts(component_dict)
    
    #STEP 3. Initiate xarray dataset 
    xr_dss= dict.fromkeys(component_dict.keys())
    for classname in component_dict:
            xr_dss[classname] = {
                component: xr.Dataset()
                for component in component_dict[classname]
            }
    
    #STEP 4. Add all df variables to xr_ds
    xr_dss = utilsIO.addDFVariablesToXarray(xr_dss, component_dict, df_iteration_dict) 

    #STEP 5. Add all series variables to xr_ds
    locations = sorted(esm_dict['locations'])
    xr_dss = utilsIO.addSeriesVariablesToXarray(xr_dss, component_dict, series_iteration_dict, locations)

    #STEP 6. Add all constant value variables to xr_ds
    xr_dss = utilsIO.addConstantsToXarray(xr_dss, component_dict, constants_iteration_dict) 

    #STEP 7. Add the data present in esm_dict as xarray attributes 
    # (These attributes contain esM init info). 
    attributes_xr = xr.Dataset()
    attributes_xr.attrs = esm_dict

    # xr_ds.attrs = esm_dict

    #STEP 8. Save to netCDF file 
    # if save:
    #     if groups:
    #         # Create netCDF file, remove existant
    #         grouped_file_path = f"{file_name}"
    #         if Path(grouped_file_path).is_file():
    #             Path(grouped_file_path).unlink()
    #         rootgrp = Dataset(grouped_file_path, "w", format="NETCDF4")
    #         rootgrp.close()

    #         for model, comps  in xr_dss.items():
    #             for component in comps.keys():
    #                 xr_dss[model][component].to_netcdf(
    #                     path=f"{file_name}",
    #                     # Datasets per component will be reflectes as groups in the NetCDF file.
    #                     group=f"Input/{model}/{component}",
    #                     # Use mode='a' to append datasets to existing file. Variables will be overwritten.
    #                     mode="a",
    #                     # Use zlib variable compression to reduce filesize with little performance loss
    #                     # for our use-case. Complevel 9 for best compression.
    #                     encoding={
    #                         var: {"zlib": True, "complevel": 9}
    #                         for var in list(xr_dss[model][component].data_vars)
    #                     },
    #                 )
    #     else:
    #         dataset_input_to_netcdf(xr_ds, file_name)

    xr_dss = {"Input": xr_dss, "Parameters": attributes_xr}
        
    yield xr_dss

    close_dss(xr_dss)

@contextmanager
def esm_output_to_datasets(esM, optSumOutputLevel=0, optValOutputLevel=1):
    # Create the netCDF file and the xr.Dataset dict for all components
    xr_dss = dict.fromkeys(esM.componentModelingDict.keys())
    for model_dict in esM.componentModelingDict.keys():
        xr_dss[model_dict] = {
            key: xr.Dataset()
            for key in esM.componentModelingDict[model_dict].componentsDict.keys()
        }

    # Write output from esM.getOptimizationSummary to datasets
    for name in esM.componentModelingDict.keys():
        utils.output("\tProcessing " + name + " ...", esM.verbose, 0)
        oL = optSumOutputLevel
        oL_ = oL[name] if type(oL) == dict else oL
        optSum = esM.getOptimizationSummary(name, outputLevel=oL_)
        if esM.componentModelingDict[name].dimension == "1dim":
            for component in optSum.index.get_level_values(0).unique():
                
                variables = optSum.loc[component].index.get_level_values(0)
                units = optSum.loc[component].index.get_level_values(1)
                variables_unit = dict(zip(variables,units))
                
                for variable in (
                    optSum.loc[component].index.get_level_values(0).unique()
                ):
                    df = optSum.loc[(component, variable)]
                    df = df.iloc[-1]
                    df.name = variable
                    df.index.rename("space", inplace=True)
                    df = pd.to_numeric(df)
                    xr_da = df.to_xarray()

                    # add variable [e.g. 'TAC'] and units to attributes of xarray
                    unit = variables_unit[variable]
                    xr_da.attrs[variable] = unit

                    xr_dss[name][component] = xr.merge([xr_dss[name][component], xr_da],combine_attrs='drop_conflicts')
        elif esM.componentModelingDict[name].dimension == "2dim":
            for component in optSum.index.get_level_values(0).unique():

                variables = optSum.loc[component].index.get_level_values(0)
                units = optSum.loc[component].index.get_level_values(1)
                variables_unit = dict(zip(variables,units))

                for variable in (
                    optSum.loc[component].index.get_level_values(0).unique()
                ):
                    df = optSum.loc[(component, variable)]
                    if len(df.index.get_level_values(0).unique()) > 1:
                        idx = df.index.get_level_values(0).unique()[-1]
                        df = df.xs(idx, level=0)
                    else:
                        df.index = df.index.droplevel(0)
                    # df = df.iloc[-1]
                    df = df.stack()
                    # df.name = (name, component, variable)
                    df.name = variable
                    df.index.rename(["space", "space_2"], inplace=True)
                    df = pd.to_numeric(df)
                    xr_da = df.to_xarray()

                    # add variable [e.g. 'TAC'] and units to attributes of xarray
                    unit = variables_unit[variable]
                    xr_da.attrs[variable] = unit

                    xr_dss[name][component] = xr.merge([xr_dss[name][component], xr_da],combine_attrs='drop_conflicts')

        # Write output from esM.esM.componentModelingDict[name].getOptimalValues() to datasets
        data = esM.componentModelingDict[name].getOptimalValues()
        oL = optValOutputLevel
        oL_ = oL[name] if type(oL) == dict else oL
        dataTD1dim, indexTD1dim, dataTD2dim, indexTD2dim = [], [], [], []
        dataTI, indexTI = [], []
        for key, d in data.items():
            if d["values"] is None:
                continue
            if d["timeDependent"]:
                if d["dimension"] == "1dim":
                    dataTD1dim.append(d["values"]), indexTD1dim.append(key)
                elif d["dimension"] == "2dim":
                    dataTD2dim.append(d["values"]), indexTD2dim.append(key)
            else:
                dataTI.append(d["values"]), indexTI.append(key)
        # One dimensional time dependent data
        if dataTD1dim:
            names = ["Variable", "Component", "Location"]
            dfTD1dim = pd.concat(dataTD1dim, keys=indexTD1dim, names=names)
            dfTD1dim = dfTD1dim.loc[
                ((dfTD1dim != 0) & (~dfTD1dim.isnull())).any(axis=1)
            ]
            for variable in dfTD1dim.index.get_level_values(0).unique():
                # for component in dfTD1dim.index.get_level_values(1).unique():
                for component in dfTD1dim.loc[variable].index.get_level_values(0).unique():
                    df = dfTD1dim.loc[(variable, component)].T.stack()
                    # df.name = (name, component, variable)
                    df.name = variable
                    df.index.rename(["time", "space"], inplace=True)
                    xr_da = df.to_xarray()
                    xr_dss[name][component] = xr.merge([xr_dss[name][component], xr_da])
        # Two dimensional time dependent data
        if dataTD2dim:
            names = ["Variable", "Component", "LocationIn", "LocationOut"]
            dfTD2dim = pd.concat(dataTD2dim, keys=indexTD2dim, names=names)
            dfTD2dim = dfTD2dim.loc[
                ((dfTD2dim != 0) & (~dfTD2dim.isnull())).any(axis=1)
            ]
            for variable in dfTD2dim.index.get_level_values(0).unique():
                # for component in dfTD2dim.index.get_level_values(1).unique():
                for component in dfTD2dim.loc[variable].index.get_level_values(0).unique():
                    df = dfTD2dim.loc[(variable, component)].stack()
                    # df.name = (name, component, variable)
                    df.name = variable
                    df.index.rename(["space", "space_2", "time"], inplace=True)
                    df.index = df.index.reorder_levels([2, 0, 1])
                    xr_da = df.to_xarray()
                    xr_dss[name][component] = xr.merge([xr_dss[name][component], xr_da])
        # Time independent data
        if dataTI:
            # One dimensional
            if esM.componentModelingDict[name].dimension == "1dim":
                names = ["Variable type", "Component"]
                dfTI = pd.concat(dataTI, keys=indexTI, names=names)
                dfTI = dfTI.loc[((dfTI != 0) & (~dfTI.isnull())).any(axis=1)]
                for variable in dfTI.index.get_level_values(0).unique():
                    # for component in dfTI.index.get_level_values(1).unique():
                    for component in dfTI.loc[variable].index.get_level_values(0).unique():
                        df = dfTI.loc[(variable, component)].T
                        # df.name = (name, component, variable)
                        df.name = variable
                        df.index.rename("space", inplace=True)
                        xr_da = df.to_xarray()
                        xr_dss[name][component] = xr.merge(
                            [xr_dss[name][component], xr_da]
                        )
            # Two dimensional
            elif esM.componentModelingDict[name].dimension == "2dim":
                names = ["Variable type", "Component", "Location"]
                dfTI = pd.concat(dataTI, keys=indexTI, names=names)
                dfTI = dfTI.loc[((dfTI != 0) & (~dfTI.isnull())).any(axis=1)]
                for variable in dfTI.index.get_level_values(0).unique():
                    #for component in dfTI.index.get_level_values(1).unique():
                    for component in dfTI.loc[variable].index.get_level_values(0).unique():
                        df = dfTI.loc[(variable, component)].T.stack()
                        # df.name = (name, component, variable)
                        df.name = variable
                        df.index.rename(["space", "space_2"], inplace=True)
                        xr_da = df.to_xarray()
                        xr_dss[name][component] = xr.merge(
                            [xr_dss[name][component], xr_da]
                        )

    for name in esM.componentModelingDict.keys():
        for component in esM.componentModelingDict[name].componentsDict.keys():
            if list(xr_dss[name][component].data_vars) == []:
                # Delete components that have not been built.
                del xr_dss[name][component]
            else:
        # Cast space coordinats to str. If this is not done then dtype will be object.
                xr_dss[name][component].coords["space"] = (
                    xr_dss[name][component].coords["space"].astype(str)
                )
                if esM.componentModelingDict[name].dimension == "2dim":
                    xr_dss[name][component].coords["space_2"] = (
                        xr_dss[name][component].coords["space_2"].astype(str)
                    )

    xr_dss = {"Results": xr_dss}

    yield xr_dss

    close_dss(xr_dss)

def datasets_to_netcdf(xr_dss, file_path="my_esm.nc", remove_existing=False, mode="a", group_prefix=None):

    # Create netCDF file, remove existant
    if remove_existing:
        if Path(file_path).is_file():
            Path(file_path).unlink()

    if not Path(file_path).is_file():
            with Dataset(file_path, "w", format="NETCDF4") as rootgrp:
                pass

    # rootgrp = Dataset(file_path, "w", format="NETCDF4")
    # rootgrp.close()

    for group in xr_dss.keys(): 
        if group == "Parameters":

            xarray_dataset = xr_dss[group]
            _xarray_dataset = xarray_dataset.copy() #Copying to avoid errors due to change of size during iteration

            for attr_name, attr_value in _xarray_dataset.attrs.items():
                
                #if the attribute is set, convert into sorted list 
                if isinstance(attr_value, set):
                    xarray_dataset.attrs[attr_name] = sorted(xarray_dataset.attrs[attr_name])

                #if the attribute is dict, convert into a "flattened" list 
                elif isinstance(attr_value, dict):
                    xarray_dataset.attrs[attr_name] = \
                        list(f"{k} : {v}" for (k,v) in xarray_dataset.attrs[attr_name].items())

                #if the attribute is pandas series, add a new attribute corresponding 
                # to each row.  
                elif isinstance(attr_value, pd.Series):
                    for idx, value in attr_value.items():
                        xarray_dataset.attrs.update({f"{attr_name}.{idx}" : value})

                    # Delete the original attribute  
                    del xarray_dataset.attrs[attr_name] 

                #if the attribute is pandas df, add a new attribute corresponding 
                # to each row by converting the column into a numpy array.   
                elif isinstance(attr_value, pd.DataFrame):
                    _df = attr_value
                    _df = _df.reindex(sorted(_df.columns), axis=1)
                    for idx, row in _df.iterrows():
                        xarray_dataset.attrs.update({f"{attr_name}.{idx}" : row.to_numpy()})

                    # Delete the original attribute  
                    del xarray_dataset.attrs[attr_name]

                #if the attribute is bool, add a corresponding string  
                elif isinstance(attr_value, bool):
                    xarray_dataset.attrs[attr_name] = "True" if attr_value == True else "False"
                
                #if the attribute is None, add a corresponding string  
                elif attr_value == None:
                    xarray_dataset.attrs[attr_name] = "None"

            if group_prefix:
                group_path=f"{group_prefix}/{group}"
            else:
                group_path=f"{group}"

            xarray_dataset.to_netcdf(
                path=f"{file_path}",
                # Datasets per component will be reflectes as groups in the NetCDF file.
                group=group_path,
                # Use mode='a' to append datasets to existing file. Variables will be overwritten.
                mode=mode,
                # Use zlib variable compression to reduce filesize with little performance loss
                # for our use-case. Complevel 9 for best compression.
                # encoding={
                #     var: {"zlib": True, "complevel": 9}
                #     for var in list(xr_dss[group].data_vars)
                # },
            )
            continue

        else:
            for model, comps  in xr_dss[group].items():
                for component in comps.keys():
                    if component is not None:
                        if group_prefix:
                            group_path=f"{group_prefix}/{group}/{model}/{component}"
                        else:
                            group_path=f"{group}/{model}/{component}"
                        xr_dss[group][model][component].to_netcdf(
                            path=f"{file_path}",
                            # Datasets per component will be reflectes as groups in the NetCDF file.
                            group=group_path,
                            # Use mode='a' to append datasets to existing file. Variables will be overwritten.
                            mode=mode,
                            # Use zlib variable compression to reduce filesize with little performance loss
                            # for our use-case. Complevel 9 for best compression.
                            encoding={
                                var: {"zlib": True, "complevel": 9}
                                for var in list(xr_dss[group][model][component].data_vars)
                            },
                        )

    close_dss(xr_dss)

def datasets_to_esm(xr_dss):

    # Read parameters
    xarray_dataset = utilsIO.processXarrayAttributes(xr_dss["Parameters"])
    esm_dict = xarray_dataset.attrs

    # Read input
    # Iterate through each component-variable pair, depending on the variable's prefix 
    # restructure the data and add it to component_dict 
    component_dict = utilsIO.PowerDict()

    for group in xr_dss.keys(): 
        if (group != "Parameters") and (group == "Input"):
            for model, comps  in xr_dss[group].items():
                for component_name,  comp_xr in xr_dss[group][model].items():
                    for variable, comp_var_xr in comp_xr.data_vars.items():
                        if not pd.isnull(comp_var_xr.values).all(): # Skip if all are NAs 

                            component = f"{model}, {component_name}" 
                            
                            #STEP 4 (i). Set regional time series (region, time)
                            if variable[:3]== 'ts_':
                                component_dict = \
                                    utilsIO.addTimeSeriesVariableToDict(component_dict, comp_var_xr, component, variable, drop_component=False)
                        
                            #STEP 4 (ii). Set 2d data (region, region)
                            elif variable[:3]== '2d_':
                                component_dict = \
                                    utilsIO.add2dVariableToDict(component_dict, comp_var_xr, component, variable, drop_component=False)
                                
                            #STEP 4 (iii). Set 1d data (region)
                            elif variable[:3]== '1d_':
                                component_dict = \
                                    utilsIO.add1dVariableToDict(component_dict, comp_var_xr, component, variable, drop_component=False)

                            #STEP 4 (iv). Set 0d data 
                            elif variable[:3]== '0d_':
                                component_dict = \
                                    utilsIO.add0dVariableToDict(component_dict, comp_var_xr, component, variable)


    # Create esm from esm_dict and component_dict
    esM = dictIO.importFromDict(esm_dict, component_dict)

    # Read output
    if 'Results' in xr_dss:
        for model, comps in xr_dss['Results'].items():

            # read opt Summary
            optSum_df = pd.DataFrame([])
            for component in xr_dss['Results'][model]:
                optSum_df_comp = pd.DataFrame([])
                for variable in xr_dss['Results'][model][component]:
                    if 'Optimum' in variable:
                        continue
                    if 'space_2' in list(xr_dss['Results'][model][component].coords):
                        _optSum_df = xr_dss['Results']['TransmissionModel'][component][variable].to_dataframe().unstack()
                        iterables = [[component,variable,unit] for variable,unit in xr_dss['Results'][model][component][variable].attrs.items()]                    
                        iterables2 = [[iterables[0] + [location]][0] for location in xr_dss['Results'][model][component][variable]['space'].values]
                        idx = pd.MultiIndex.from_tuples(tuple(iterables2))
                        _optSum_df.index  = idx
                        _optSum_df.index.names = ['Component','Property','Unit','LocationIn']
                        _optSum_df = _optSum_df.droplevel(0,axis=1)
                        optSum_df_comp = optSum_df_comp.append(_optSum_df)
                    else:
                        _optSum_df = xr_dss['Results'][model][component][variable].to_dataframe().T
                        iterables = [[component,variable,unit] for variable,unit in xr_dss['Results'][model][component][variable].attrs.items()]                    
                        _optSum_df.index = pd.MultiIndex.from_tuples(iterables)
                        _optSum_df.index.names = ['Component','Property','Unit']
                        optSum_df_comp = optSum_df_comp.append(_optSum_df)

                optSum_df = optSum_df.append(optSum_df_comp)  

            setattr(esM.componentModelingDict[model], 'optSummary',optSum_df)

            # read optimal Values (3 types exist)
            operationVariablesOptimum_df = pd.DataFrame([])
            capacityVariablesOptimum_df = pd.DataFrame([])
            isBuiltVariablesOptimum_df = pd.DataFrame([])
            chargeOperationVariablesOptimum_df = pd.DataFrame([])
            dischargeOperationVariablesOptimum_df = pd.DataFrame([])
            stateOfChargeOperationVariablesOptimum_df = pd.DataFrame([])
            
            for component in xr_dss['Results'][model]:

                _operationVariablesOptimum_df =  pd.DataFrame([])
                _capacityVariablesOptimum_df =  pd.DataFrame([])
                _isBuiltVariablesOptimum_df =  pd.DataFrame([])
                _chargeOperationVariablesOptimum_df =  pd.DataFrame([])
                _dischargeOperationVariablesOptimum_df =  pd.DataFrame([])
                _stateOfChargeOperationVariablesOptimum_df =  pd.DataFrame([])

                for variable in xr_dss['Results'][model][component]:
                    if 'Optimum' not in variable:
                        continue
                    opt_variable = variable
                    xr_opt = None
                    if opt_variable in xr_dss['Results'][model][component]:
                        xr_opt = xr_dss['Results'][model][component][opt_variable]
                    else:
                        continue
                    
                    if opt_variable == 'operationVariablesOptimum':
                        if 'space_2' in list(xr_opt.coords):
                            df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                            _operationVariablesOptimum_df = pd.DataFrame([])
                            for item in df.index.get_level_values(0).unique():
                                _df= df.loc[item]
                                _df = _df.drop(item)
                                idx = pd.MultiIndex.from_product([[component],[item],list(_df.index)])
                                _df = _df.set_index(idx)
                                _operationVariablesOptimum_df = _operationVariablesOptimum_df.append(_df)

                        else:    
                            _operationVariablesOptimum_df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                            _operationVariablesOptimum_df = _operationVariablesOptimum_df.dropna(axis=0)
                            idx = pd.MultiIndex.from_product([[component],_operationVariablesOptimum_df.index])
                            _operationVariablesOptimum_df = _operationVariablesOptimum_df.set_index(idx)

                    if opt_variable == 'capacityVariablesOptimum':
                        if 'space_2' in list(xr_opt.coords):
                            df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                            idx = pd.MultiIndex.from_product([[component],list(df.index)])
                            _df = df.set_index(idx)
                            _capacityVariablesOptimum_df = _df
                        else:
                            _capacityVariablesOptimum_df = xr_opt.to_dataframe().T
                            _capacityVariablesOptimum_df = _capacityVariablesOptimum_df.set_axis([component])

                    if opt_variable == 'isBuiltVariablesOptimum':
                        _isBuiltVariablesOptimum_df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                        idx = pd.MultiIndex.from_product([[component],_isBuiltVariablesOptimum_df.index])
                        _isBuiltVariablesOptimum_df = _isBuiltVariablesOptimum_df.set_index(idx)

                    if opt_variable == 'chargeOperationVariablesOptimum':
                        _chargeOperationVariablesOptimum_df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                        idx = pd.MultiIndex.from_product([[component],_chargeOperationVariablesOptimum_df.index])
                        _chargeOperationVariablesOptimum_df = _chargeOperationVariablesOptimum_df.set_index(idx)

                    if opt_variable == 'dischargeOperationVariablesOptimum':
                        _dischargeOperationVariablesOptimum_df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                        idx = pd.MultiIndex.from_product([[component],_dischargeOperationVariablesOptimum_df.index])
                        _dischargeOperationVariablesOptimum_df = _dischargeOperationVariablesOptimum_df.set_index(idx)
                    
                    if opt_variable == 'stateOfChargeOperationVariablesOptimum':
                        _stateOfChargeOperationVariablesOptimum_df = xr_opt.to_dataframe().unstack(level=0).droplevel(0,axis=1)
                        idx = pd.MultiIndex.from_product([[component],_stateOfChargeOperationVariablesOptimum_df.index])
                        _stateOfChargeOperationVariablesOptimum_df = _stateOfChargeOperationVariablesOptimum_df.set_index(idx)                    

                operationVariablesOptimum_df = operationVariablesOptimum_df.append(_operationVariablesOptimum_df)
                capacityVariablesOptimum_df = capacityVariablesOptimum_df.append(_capacityVariablesOptimum_df)
                isBuiltVariablesOptimum_df = isBuiltVariablesOptimum_df.append(_isBuiltVariablesOptimum_df)
                chargeOperationVariablesOptimum_df = chargeOperationVariablesOptimum_df.append(_chargeOperationVariablesOptimum_df)
                dischargeOperationVariablesOptimum_df = dischargeOperationVariablesOptimum_df.append(_dischargeOperationVariablesOptimum_df)
                stateOfChargeOperationVariablesOptimum_df = stateOfChargeOperationVariablesOptimum_df.append(_stateOfChargeOperationVariablesOptimum_df)

            # check if empty, if yes convert to None
            if operationVariablesOptimum_df.empty: operationVariablesOptimum_df = None
            if capacityVariablesOptimum_df.empty: capacityVariablesOptimum_df = None
            if isBuiltVariablesOptimum_df.empty: isBuiltVariablesOptimum_df = None
            if chargeOperationVariablesOptimum_df.empty: chargeOperationVariablesOptimum_df = None
            if dischargeOperationVariablesOptimum_df.empty: dischargeOperationVariablesOptimum_df = None
            if stateOfChargeOperationVariablesOptimum_df.empty: stateOfChargeOperationVariablesOptimum_df = None
                
            setattr(esM.componentModelingDict[model], 'operationVariablesOptimum', operationVariablesOptimum_df)
            setattr(esM.componentModelingDict[model], 'capacityVariablesOptimum', capacityVariablesOptimum_df)
            setattr(esM.componentModelingDict[model], 'isBuiltVariablesOptimum', isBuiltVariablesOptimum_df)
            setattr(esM.componentModelingDict[model], 'chargeOperationVariablesOptimum', chargeOperationVariablesOptimum_df)
            setattr(esM.componentModelingDict[model], 'dischargeOperationVariablesOptimum', dischargeOperationVariablesOptimum_df)
            setattr(esM.componentModelingDict[model], 'stateOfChargeOperationVariablesOptimum', stateOfChargeOperationVariablesOptimum_df)


    return esM


def esm_to_netcdf(
    esM,
    file_path="my_esm.nc",
    overwrite_existing=False,
    optSumOutputLevel=0,
    optValOutputLevel=1,
    group_prefix=None
) -> Dict[str, Dict[str, xr.Dataset]]:
    """
    Write esm to netCDF file.

    :param esM: EnergySystemModel instance in which the optimized model is hold
    :type esM: EnergySystemModel instance

    :param outputFileName: Name of the netCDF output file 
        |br| * the default value is 'scenarioOutput'
    :type outputFileName: string

    :param overwrite_existing: Overwrite existing netCDF file 
        |br| * the default value is 'scenarioOutput'
    :type outputFileName: string

    :param optSumOutputLevel: Output level of the optimization summary (see EnergySystemModel). Either an integer
        (0,1,2) which holds for all model classes or a dictionary with model class names as keys and an integer
        (0,1,2) for each key (e.g. {'StorageModel':1,'SourceSinkModel':1,...}
        |br| * the default value is 2
    :type optSumOutputLevel: int (0,1,2) or dict

    :param optValOutputLevel: Output level of the optimal values. Either an integer (0,1) which holds for all
        model classes or a dictionary with model class names as keys and an integer (0,1) for each key
        (e.g. {'StorageModel':1,'SourceSinkModel':1,...}
        - 0: all values are kept.
        - 1: Lines containing only zeroes are dropped.
        |br| * the default value is 1
    :type optValOutputLevel: int (0,1) or dict

    :return: Nested dictionary containing an xr.Dataset with all result values for each component.
    :rtype: Dict[str, Dict[str, xr.Dataset]]
    """

    if overwrite_existing:
        if Path(file_path).is_file():
            Path(file_path).unlink()

    utils.output("\nWriting output to netCDF... ", esM.verbose, 0)
    _t = time.time()

    with esm_input_to_datasets(esM) as xr_dss_input:
        datasets_to_netcdf(xr_dss_input, file_path,group_prefix=group_prefix)

    if esM.objectiveValue != None: # model was  optimized
        with esm_output_to_datasets(esM, optSumOutputLevel, optValOutputLevel) as xr_dss_output:
            datasets_to_netcdf(xr_dss_output, file_path,group_prefix=group_prefix)

    utils.output("Done. (%.4f" % (time.time() - _t) + " sec)", esM.verbose, 0)

@contextmanager
def esm_to_datasets(esM):
    with esm_output_to_datasets(esM) as xr_dss_output, esm_input_to_datasets(esM) as xr_dss_input :
        xr_dss_results = {"Results": xr_dss_output["Results"], "Input": xr_dss_input["Input"], "Parameters": xr_dss_input["Parameters"]}
        yield xr_dss_results

@contextmanager
def netcdf_to_datasets(
    file_path="my_esm.nc", group_prefix=None
) -> Dict[str, Dict[str, xr.Dataset]]:
    """Read optimization results from grouped netCDF file to dictionary of xr.Datasets.

    :param inputFileName: Path to input netCDF file, defaults to "esM_results.nc4"
    :type inputFileName: str, optional

    :return: Nested dictionary containing an xr.Dataset with all result values for each component.
    :rtype: Dict[str, Dict[str, xr.Dataset]]
    """

    with Dataset(file_path, "r", format="NETCDF4") as rootgrp:
        if group_prefix:
            group_keys = rootgrp[group_prefix].groups
        else:
            group_keys = rootgrp.groups

    if not group_prefix:
        xr_dss = {group_key: 
                    {model_key: 
                        {comp_key: 
                            xr.open_dataset(file_path, group=f"{group_key}/{model_key}/{comp_key}")
                        for comp_key in group_keys[group_key][model_key].groups}
                    for model_key in group_keys[group_key].groups} 
                for group_key in group_keys if group_key != "Parameters"}
        xr_dss["Parameters"] =  xr.open_dataset(file_path, group=f"Parameters")
    else:
        xr_dss = {group_key: 
                    {model_key: 
                        {comp_key: 
                            xr.open_dataset(file_path, group=f"{group_prefix}/{group_key}/{model_key}/{comp_key}")
                        for comp_key in group_keys[group_key][model_key].groups}
                    for model_key in group_keys[group_key].groups} 
                for group_key in group_keys if group_key != "Parameters"}
        xr_dss["Parameters"] =  xr.open_dataset(file_path, group=f"{group_prefix}/Parameters")

    yield xr_dss

    close_dss(xr_dss)


def netcdf_to_esm(file_path, group_prefix=None):
    with netcdf_to_datasets(file_path, group_prefix) as dss:
        esm = datasets_to_esm(dss)
    return esm
