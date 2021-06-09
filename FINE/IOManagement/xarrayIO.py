import numpy as np
from numpy.core.defchararray import array
import pandas as pd
import xarray as xr

from FINE import utils
from FINE.IOManagement import dictIO

def saveNetcdfFile(xarray_dataset,  file_name='esM_instance.nc4'):
    """Saves the given xarray dataset as a netcdf file 
    
    :param xarray_dataset: The dataset holding all data required to set up an esM instance. 
        Can be a read-in xarray dataset. Alternatively, full path to a netcdf file is also acceptable. 
    :type xarray_dataset: xr.Dataset or string 

    :param file_name: output file name (can include full path)
        |br| * the default value is 'esM_instance.nc4'
    :type file_name: string
    """

    #NOTE: data types such as sets, dicts, bool, pandas df/series and Nonetype
    #  are not serializable. Therefore, they are converted to lists/strings while saving

    xarray_dataset.attrs['locations'] = sorted(xarray_dataset.attrs['locations'])
    xarray_dataset.attrs['commodities'] = sorted(xarray_dataset.attrs['commodities'])

    xarray_dataset.attrs['commodityUnitsDict'] = \
        list(f"{k} : {v}" for (k,v) in xarray_dataset.attrs['commodityUnitsDict'].items())

    if isinstance(xarray_dataset.attrs['balanceLimit'], pd.Series):
        for idx, value in xarray_dataset.attrs['balanceLimit'].items():
            xarray_dataset.attrs.update({f"balanceLimit_{idx}" : value})
    
    elif isinstance(xarray_dataset.attrs['balanceLimit'], pd.DataFrame):
        df = xarray_dataset.attrs['balanceLimit']
        df = df.reindex(sorted(df.columns), axis=1)
        for idx, row in xarray_dataset.attrs['balanceLimit'].iterrows():
            xarray_dataset.attrs.update({f"balanceLimit_{idx}" : row.to_numpy()})
    
    del xarray_dataset.attrs['balanceLimit']  

    xarray_dataset.attrs['lowerBound'] = "True" if xarray_dataset.attrs['lowerBound'] == True else "False"
    xarray_dataset.to_netcdf(file_name)



def generateIterationDicts(component_dict):
    """Creates iteration dictionaries that contain descriptions of all 
    dataframes, series, and constants present in component_dict.
    
    :param component_dict: dictionary containing information about the esM instance's components
    :type component_dict: dict
 
    :return: df_iteration_dict, series_iteration_dict, constants_iteration_dict
    """
    
    df_iteration_dict, series_iteration_dict, constants_iteration_dict = {}, {}, {}

    # Loop through every class-component-variable combination 
    for classname in component_dict:

        for component in component_dict[classname]:            

            for variable_description, data in component_dict[classname][component].items():
                description_tuple = (classname, component)
                
                #private function to check if the current variable is a dict, df, series or constant. 
                # If its a dict (in the case of commodityConversionFactors), this is unpacked and the 
                # the function is run on each value in dict 
                def _append_to_iteration_dicts(_variable_description, _data):

                    if isinstance(_data, dict):
                        for key, value in _data.items():
                            nested_variable_description = f'{_variable_description}.{key}' #NOTE: a . is introduced in the variable here  

                            _append_to_iteration_dicts(nested_variable_description, value)

                    elif isinstance(_data, pd.DataFrame):
                        if _variable_description not in df_iteration_dict.keys():
                            df_iteration_dict[_variable_description] = [description_tuple]
                        else:
                            df_iteration_dict[_variable_description].append(description_tuple)
                    
                    #NOTE: transmission components are series in component_dict 
                    # (example index - cluster_0_cluster_2)
                    
                    elif isinstance(_data, pd.Series):       
                        if _variable_description not in series_iteration_dict.keys():
                            series_iteration_dict[_variable_description] = [description_tuple]
                        else:
                            series_iteration_dict[_variable_description].append(description_tuple)
                            
                    else:
                        if _variable_description not in constants_iteration_dict.keys():
                            constants_iteration_dict[_variable_description] = [description_tuple]
                        else:
                            constants_iteration_dict[_variable_description].append(description_tuple)

                _append_to_iteration_dicts(variable_description, data)


    return df_iteration_dict, series_iteration_dict, constants_iteration_dict



def convertEsmInstanceToXarrayDataset(esM, save=False, file_name='esM_instance.nc4'):  
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
 
    :return: ds - esM instance data in xarray dataset format 
    """
    
    #STEP 1. Get the esm and component dicts 
    esm_dict, component_dict = dictIO.exportToDict(esM)

    locations = sorted(esm_dict['locations'])

    #STEP 2. Get the iteration dicts 
    df_iteration_dict, series_iteration_dict, constants_iteration_dict = generateIterationDicts(component_dict)
    
    #STEP 3. Iterate through each iteration dicts and add the data to a xarray Dataset.
    # data comes from component_dict
    ds = xr.Dataset()

    #STEP 3a. Add all regional time series (dimensions - space, time)
    for variable_description, description_tuple_list in df_iteration_dict.items():
        df_dict = {} 

        for description_tuple in description_tuple_list:
            classname, component = description_tuple

            df_description = f"{classname}, {component}"
            
            # If a . is present in variable name, then the data would be another level further in the component_dict 
            if '.' in variable_description:      
                nested_variable_description = variable_description.split('.')
                data = component_dict[classname][component][nested_variable_description[0]][nested_variable_description[1]]
            else:
                data = component_dict[classname][component][variable_description]

            multi_index_dataframe = data.stack()
            multi_index_dataframe.index.set_names("time", level=0, inplace=True)
            multi_index_dataframe.index.set_names("space", level=1, inplace=True)
            
            df_dict[df_description] = multi_index_dataframe 
                                        
        df_variable = pd.concat(df_dict)
        df_variable.index.set_names("component", level=0, inplace=True) 

        ds_component = xr.Dataset()
        ds_component[f"ts_{variable_description}"] = df_variable.sort_index().to_xarray()

        ds = xr.merge([ds, ds_component])

    #STEP 3b. Add all 2d data (dimensions - space, space)
    for variable_description, description_tuple_list in series_iteration_dict.items():
        df_dict = {} 
    
        for description_tuple in description_tuple_list:
            classname, component = description_tuple

            df_description = f"{classname}, {component}"

            if '.' in variable_description:
                nested_variable_description = variable_description.split('.')
                data = component_dict[classname][component][nested_variable_description[0]][nested_variable_description[1]]
            else:
                data = component_dict[classname][component][variable_description]

            
            if classname in ['Transmission', 'LinearOptimalPowerFlow']:    #NOTE: only ['Transmission', 'LinearOptimalPowerFlow'] are 2d classes 

                df = utils.transform1dSeriesto2dDataFrame(data, locations)
                multi_index_dataframe = df.stack()
                multi_index_dataframe.index.set_names(["space", "space_2"], inplace=True)

                df_dict[df_description] = multi_index_dataframe

        if len(df_dict) > 0:
            df_variable = pd.concat(df_dict)
            df_variable.index.set_names("component", level=0, inplace=True) 
            ds_component = xr.Dataset()
            ds_component[f"2d_{variable_description}"] = df_variable.sort_index().to_xarray()  #NOTE: prefix 2d and 1d are added in this function

            ds = xr.merge([ds, ds_component])

    #STEP 3c. Add all 1d data (dimension - space) or time series (dimension - space (1) and time)
    for variable_description, description_tuple_list in series_iteration_dict.items():

        df_space_dict = {} 
        df_time_dict = {} 
        for description_tuple in description_tuple_list:
            classname, component = description_tuple
    
            df_description = f"{classname}, {component}"

            if '.' in variable_description:
                nested_variable_description = variable_description.split(".")
                data = component_dict[classname][component][nested_variable_description[0]][nested_variable_description[1]]
            else:
                data = component_dict[classname][component][variable_description]

            if classname not in ['Transmission', 'LinearOptimalPowerFlow']:
                if sorted(list(locations)) == sorted(list(data.index.values)):
                    df_space_dict[df_description] = data.rename_axis("space")
                else:
                    df_time_dict[df_description] = data.rename_axis("time")
                    df_time_dict[df_description] = pd.concat({locations[0]: df_time_dict[df_description]}, names=['space'])
                    df_time_dict[df_description] = df_time_dict[df_description].reorder_levels(["time", "space"])
            
        if len(df_space_dict) > 0:
            df_variable = pd.concat(df_space_dict)
            df_variable.index.set_names("component", level=0, inplace=True) 
            ds_component = xr.Dataset()
            ds_component[f"1d_{variable_description}"] = df_variable.sort_index().to_xarray()
            
            ds = xr.merge([ds, ds_component])

        if len(df_time_dict) > 0:
            df_variable = pd.concat(df_time_dict)
            df_variable.index.set_names("component", level=0, inplace=True) 
            ds_component = xr.Dataset()
            ds_component[f"ts_{variable_description}"] = df_variable.sort_index().to_xarray()
            
            ds = xr.merge([ds, ds_component])

    #STEP 3e. Add all constants 
    for variable_description, description_tuple_list in constants_iteration_dict.items():
        
        df_dict = {} 
        for description_tuple in description_tuple_list:
            classname, component = description_tuple
            df_description = f"{classname}, {component}"

            if '.' in variable_description:
                nested_variable_description = variable_description.split(".")
                data = component_dict[classname][component][nested_variable_description[0]][nested_variable_description[1]]
            else:
                data = component_dict[classname][component][variable_description]

            df_dict[df_description] = data
            
        if len(df_dict) > 0:
            df_variable = pd.Series(df_dict)      
            df_variable.index.set_names("component", inplace=True)
            
            ds_component = xr.Dataset()
            ds_component[f"0d_{variable_description}"] = xr.DataArray.from_series(df_variable)
            
            ds = xr.merge([ds, ds_component])
            
    #STEP 4. Add the data present in esm_dict as xarray attributes (these are dimensionless data). 
    ds.attrs = esm_dict

    if save:
        saveNetcdfFile(ds, file_name)
        
    return ds



def convertXarrayDatasetToEsmInstance(xarray_dataset):
    """Takes as its input xarray dataset or path to a netcdf file, converts it into an esM instance. 
    
    :param xarray_dataset: The dataset holding all data required to set up an esM instance. 
        Can be a read-in xarray dataset. Alternatively, full path to a netcdf file is also acceptable. 
    :type xarray_dataset: xr.Dataset or string 
 
    :return: esM - EnergySystemModel instance in which the optimized model is held
    """

    #STEP 1. Read in the netcdf file
    if isinstance(xarray_dataset, str): 
        xarray_dataset = xr.open_dataset(xarray_dataset)
    
    elif not isinstance(xarray_dataset, xr.Dataset):
        raise TypeError("xarray_dataset must either be a path to a netcdf file or xarray dataset")
    
    #STEP 2. Convert data types of attributes if necessary 
    #NOTE: data types such as sets, dicts, bool, pandas df/series and Nonetype
    #  are not serializable. Therefore, they are converted to lists/strings while saving.
    # They need to be converted back to right formats 

    ## locations 
    if isinstance(xarray_dataset.attrs['locations'], list):
        xarray_dataset.attrs['locations'] = set(xarray_dataset.attrs['locations'])

    ## commodities 
    if isinstance(xarray_dataset.attrs['commodities'], list):
        xarray_dataset.attrs['commodities'] = set(xarray_dataset.attrs['commodities'])

    ## commoditiesUnitsDict 
    if isinstance(xarray_dataset.attrs['commodityUnitsDict'], list):
        new_commodityUnitsDict = {}

        for item in xarray_dataset.attrs['commodityUnitsDict']:
            [commodity, unit] = item.split(' : ')
            new_commodityUnitsDict.update({commodity : unit})

        xarray_dataset.attrs['commodityUnitsDict'] = new_commodityUnitsDict

    ## balanceLimit
    try:
        xarray_dataset.attrs['balanceLimit']

    except KeyError:
    
        balanceLimit_dict = {}
        keys_to_delete = []

        for key in xarray_dataset.attrs.keys():
            if key[:12] == 'balanceLimit':
                [bl, idx] = key.split('_') 
                balanceLimit_dict.update({idx : xarray_dataset.attrs.get(key)}) 

                keys_to_delete.append(key)

        # cleaning up the many keys belonging to balanceLimit
        for key in keys_to_delete:
            xarray_dataset.attrs.pop(key)

        if balanceLimit_dict == {}:
            xarray_dataset.attrs.update({'balanceLimit' : None})

        elif all([isinstance(value, np.ndarray) for value in list(balanceLimit_dict.values())]):   
            data = np.stack(balanceLimit_dict.values())
            columns = sorted(xarray_dataset.attrs['locations'])
            index = balanceLimit_dict.keys()

            df = pd.DataFrame(data, columns=columns, index=index)
            
            xarray_dataset.attrs.update({'balanceLimit' : df})

        else: 
            series = pd.Series(balanceLimit_dict)
            xarray_dataset.attrs.update({'balanceLimit' : series})
        
        
    ## lowerBound
    if isinstance(xarray_dataset.attrs['lowerBound'], str):
        xarray_dataset.attrs['lowerBound'] = True if xarray_dataset.attrs['lowerBound'] == "True" else False

    #NOTE: ints are converted to numpy ints while saving, but these should strictly be ints. 
    if not isinstance(xarray_dataset.attrs['numberOfTimeSteps'], int):
        xarray_dataset.attrs['numberOfTimeSteps'] = int(xarray_dataset.attrs['numberOfTimeSteps'])
    
    if not isinstance(xarray_dataset.attrs['hoursPerTimeStep'], int):
        xarray_dataset.attrs['hoursPerTimeStep'] = int(xarray_dataset.attrs['hoursPerTimeStep'])
        

    #STEP 3. Create esm_dict 
    esm_dict = xarray_dataset.attrs

    #STEP 4. Iterate through each component-variable pair, depending on the variable's prefix 
    # restructure the data and add it to component_dict 
    component_dict = utils.PowerDict()

    for component in xarray_dataset.component.values:
        comp_xr = xarray_dataset.sel(component=component)
        
        for variable, comp_var_xr in comp_xr.data_vars.items():

            if not pd.isnull(comp_var_xr.values).all():
                
                #STEP 4 (i). Set all regional time series (region, time)
                if variable[:3]== 'ts_':

                    df = comp_var_xr.drop("component").to_dataframe().unstack(level=1)
                    if len(df.columns) > 1:
                        df.columns = df.columns.droplevel(0)
                    
                    [class_name, comp_name] = component.split(', ')

                    if '.' in variable:
                        [var_name, nested_var_name] = variable.split('.')
                        component_dict[class_name][comp_name][var_name[3:]][nested_var_name] = df.sort_index()
                        #NOTE: Thanks to utils.PowerDict(), the nested dictionaries need not be created before adding the data. 

                    else:
                        component_dict[class_name][comp_name][variable[3:]] = df.sort_index()

                #STEP 4 (ii). Set all 2d data (region, region)
                elif variable[:3]== '2d_':

                    series = comp_var_xr.drop("component").to_dataframe().stack(level=0)
                    series.index = series.index.droplevel(level=2).map('_'.join)

                    #NOTE: In FINE, a check is made to make sure that locationalEligibility indices matches indices of other 
                    # attributes. Removing 0 values ensures the match. If all are 0s, empty series is fed in, leading to error. 
                    # Therefore, if series is empty, the variable is not added. 
                    series = series[series>0]  

                    if not len(series.index) == 0:

                        [class_name, comp_name] = component.split(', ')

                        if '.' in variable:
                            [var_name, nested_var_name] = variable.split('.')
                            component_dict[class_name][comp_name][var_name[3:]][nested_var_name] = series.sort_index()
                        else:
                            component_dict[class_name][comp_name][variable[3:]] = series.sort_index()

                #STEP 4 (iii). Set all 1d data (region)
                elif variable[:3]== '1d_':

                    series = comp_var_xr.drop("component").to_dataframe().unstack(level=0)
                    series.index = series.index.droplevel(level=0)

                    [class_name, comp_name] = component.split(', ')

                    if '.' in variable:
                        [var_name, nested_var_name] = variable.split('.')
                        component_dict[class_name][comp_name][var_name[3:]][nested_var_name] = series.sort_index()
                    else:
                        component_dict[class_name][comp_name][variable[3:]] = series.sort_index()

                #STEP 4 (iv). Set all 0d data 
                elif variable[:3]== '0d_':

                    var_value = comp_var_xr.values

                    if not var_value == '': #NOTE: when saving to netcdf, the nans in string arrays are converted 
                                            # to empty string (''). These need to be skipped. 
                    
                        [class_name, comp_name] = component.split(', ')

                        if '.' in variable:
                            [var_name, nested_var_name] = variable.split('.')
                            component_dict[class_name][comp_name][var_name[3:]][nested_var_name] = var_value.item()
                        else:
                            component_dict[class_name][comp_name][variable[3:]] = var_value.item()

    #STEP 5. Create esm from esm_dict and component_dict
    esM = dictIO.importFromDict(esm_dict, component_dict)

    return esM 
