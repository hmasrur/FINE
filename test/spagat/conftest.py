import pathlib
import pytest

import numpy as np
import pandas as pd
import geopandas as gpd 
import xarray as xr 
from shapely.geometry import Polygon, MultiPolygon
from collections import namedtuple

import FINE.spagat.utils as spu

#============================================Fixtures for Grouping==================================================#


@pytest.fixture()
def xr_for_connectivity():  

  component_list = ['source_comp','sink_comp', 'transmission_comp']  
  space_list = ['01_reg','02_reg','03_reg','04_reg', '05_reg','06_reg', '07_reg','08_reg']
  time_list = ['T0','T1']

  ## ts variable data
  operationRateMax = np.array([  [[1] * 8 for i in range(2)], 

                                 [[np.nan] * 8 for i in range(2)], 

                                 [[np.nan] * 8 for i in range(2)]

                          ])

  operationRateMax_da = xr.DataArray(operationRateMax, 
                                  coords=[component_list, time_list, space_list], 
                                  dims=['component', 'time', 'space'])


  ## 1d variable data
  capacityMax_1d = np.array([ [14] * 8, 
                            [np.nan] *8, 
                            [np.nan] *8
                          ])

  capacityMax_1d_da = xr.DataArray(capacityMax_1d, 
                              coords=[component_list, space_list], 
                              dims=['component', 'space'])


  ## 2d variable data
  capacityMax_2d = np.array([ [[np.nan] * 8 for i in range(8)], 

                        [[np.nan] * 8 for i in range(8)],

                         [[ 0, 0, 0, 0, 0, 0, 0, 0],
                          [ 0, 0, 0, 0, 0, 0, 0, 0],
                          [ 0, 0, 0, 0, 0, 0, 0, 0],
                          [ 0, 0, 0, 0, 0, 0, 0, 0],
                          [ 0, 0, 0, 0, 0, 0, 0, 0],
                          [ 0, 0, 0, 0, 0, 0, 0, 3],
                          [ 0, 0, 0, 0, 0, 0, 0, 5],
                          [ 0, 0, 0, 0, 0, 3, 5, 0]]
                        ])

  capacityMax_2d_da = xr.DataArray(capacityMax_2d, 
                              coords=[component_list, space_list, space_list], 
                              dims=['component', 'space', 'space_2'])
  
  locationalEligibility_2d = np.array([ [[np.nan] * 8 for i in range(8)], 

                                        [[np.nan] * 8 for i in range(8)],

                                        [[ 0, 0, 0, 0, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0.2, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0.2, 0, 0, 0, 0],
                                        [ 0, 0, 0, 0, 0, 0, 0, 0]]
                                        ])

  locationalEligibility_2d_da = xr.DataArray(locationalEligibility_2d, 
                              coords=[component_list, space_list, space_list], 
                              dims=['component', 'space', 'space_2'])
  
  test_ds = xr.Dataset({'ts_operationRateMax': operationRateMax_da, 
                        '1d_capacityMax': capacityMax_1d_da, 
                        '2d_capacityMax': capacityMax_2d_da,
                        '2d_locationalEligibility': locationalEligibility_2d_da
                        })    

  #Geometries 
  test_geometries = [Polygon([(0,3), (1,3), (1,4), (0,4)]),
                  Polygon([(1,3), (2,3), (2,4), (4,1)]),
                  Polygon([(2,3), (3,3), (3,4), (2,4)]),
                  Polygon([(0,2), (1,2), (1,3), (0,3)]),
                  Polygon([(1,2), (2,2), (2,3), (1,3)]),
                  Polygon([(2,2), (3,2), (3,3), (2,3)]),
                  Polygon([(1,0), (2,0), (2,1), (1,1)]),
                  Polygon([(2.5,0), (3.5,0), (3.5,1), (2.5,1)])] 
                

  test_ds = spu.add_objects_to_xarray(test_ds,
                                  description ='gpd_geometries',   
                                  dimension_list =['space'], 
                                  object_list = test_geometries)   
  
  test_ds = spu.add_region_centroids_to_xarray(test_ds) 
  test_ds = spu.add_centroid_distances_to_xarray(test_ds)

  return test_ds

@pytest.fixture()
def data_for_distance_measure():  
  ## ts dict            
  matrix_ts = np.array([ [1, 1], [2, 2], [3, 3] ])

  test_ts_dict = {} 
  test_ts_dict['ts_operationRateMax'] = {'Source, wind turbine' : matrix_ts, 'Source, PV' : matrix_ts}
  test_ts_dict['ts_operationRateFix'] = {'Sink, electricity demand' : matrix_ts, 'Sink, hydrogen demand' : matrix_ts}

  array_1d_2d = np.array([1, 2, 3])

  ## 1d dict
  test_1d_dict = {}            
  test_1d_dict['1d_capacityMax'] = {'Source, wind turbine' : array_1d_2d, 'Source, PV' : array_1d_2d}
  test_1d_dict['1d_capacityFix'] = {'Sink, electricity demand' : array_1d_2d, 'Sink, hydrogen demand' : array_1d_2d}

  ## 2d dict 
  test_2d_dict = {}
  test_2d_dict['2d_distance'] = {'Transmission, AC cables': array_1d_2d, 'Transmission, DC cables': array_1d_2d}
  test_2d_dict['2d_losses'] = {'Transmission, AC cables': array_1d_2d, 'Transmission, DC cables': array_1d_2d}    

  return namedtuple("test_ts_1d_2s_dicts", "test_ts_dict test_1d_dict test_2d_dict")(test_ts_dict, test_1d_dict, test_2d_dict)  


@pytest.fixture()
def xr_for_parameter_based_grouping(): 

  component_list = ['Source, wind turbine', 'Transmission, AC cables', 'Source, PV']  
  space_list = ['01_reg','02_reg','03_reg']
  time_list = ['T0','T1']

  ## time series variables data
  operationRateMax = np.array([ [[0.2, 0.1, 0.1] for i in range(2)],
                                [[np.nan]*3 for i in range(2)], 
                                [[0.2, 0.1, 0.1] for i in range(2)]  ])

  operationRateMax = xr.DataArray(operationRateMax, 
                                coords=[component_list, time_list, space_list], 
                                dims=['component', 'time','space'])
  
  
  ## 1d variable data
  capacityMax = np.array([ [1, 1, 0.2],
                          [1, 1, 0.2],
                          [1, 1, 0.2] ])

  capacityMax = xr.DataArray(capacityMax, 
                            coords=[component_list, space_list], 
                            dims=['component', 'space'])
  
  ## 2d variable data
  transmissionDistance = np.array([ [[np.nan]*3 for i in range(3)],
                                    [[0, 0.2, 0.7], 
                                      [0.2, 0, 0.2], 
                                      [0.7, 0.2, 0]],
                                  [[np.nan]*3 for i in range(3)]])

  transmissionDistance = xr.DataArray(transmissionDistance, 
                                    coords=[component_list, space_list, space_list], 
                                    dims=['component', 'space', 'space_2'])
  
  xr_ds = xr.Dataset({'ts_operationRateMax': operationRateMax,
                '1d_capacityMax': capacityMax,  
                '2d_transmissionDistance': transmissionDistance}) 

  #Geometries 
  test_geometries = [Polygon([(0,3), (1,3), (1,4), (0,4)]),
                      Polygon([(1,3), (2,3), (2,4), (4,1)]),
                      Polygon([(0,2), (1,2), (1,3), (0,3)]) ] 
                

  xr_ds = spu.add_objects_to_xarray(xr_ds,
                          description ='gpd_geometries',   
                          dimension_list =['space'], 
                          object_list = test_geometries)   
  
  xr_ds = spu.add_region_centroids_to_xarray(xr_ds) 
  xr_ds = spu.add_centroid_distances_to_xarray(xr_ds)

  return xr_ds
#============================================Fixtures for Basic Representation==================================================#

@pytest.fixture()
def xr_and_dict_for_basic_representation():  
  '''
  xarray to test basic representation functions-
  1. test_aggregate_based_on_sub_to_sup_region_id_dict()
  2. test_aggregate_time_series()
  3. test_aggregate_values()
  4. test_aggregate_connections()
  5. test_create_grid_shapefile()
  5. test_aggregate_geometries()
  '''
  #DICT
  sub_to_sup_region_id_dict = {'01_reg_02_reg': ['01_reg','02_reg'], 
                                 '03_reg_04_reg': ['03_reg','04_reg']}
  
  #xr
  component_list = ['source_comp','sink_comp', 'transmission_comp']  
  space_list = ['01_reg','02_reg','03_reg','04_reg']
  time_list = ['T0','T1']

  ## ts variable data
  operationRateMax = np.array([  [ [3, 3, 3, 3] for i in range(2)] ,

                           [[np.nan, np.nan, np.nan, np.nan] for i in range(2)], 

                           [[np.nan, np.nan, np.nan, np.nan] for i in range(2)]

                          ])

  operationRateMax_da = xr.DataArray(operationRateMax, 
                                  coords=[component_list, time_list, space_list], 
                                  dims=['component', 'time','space'])

  operationRateFix = np.array([  [[np.nan, np.nan, np.nan, np.nan] for i in range(2)], 

                          [  [5, 5, 5, 5] for i in range(2)],

                           [[np.nan, np.nan, np.nan, np.nan] for i in range(2)]

                          ])

  operationRateFix_da = xr.DataArray(operationRateFix, 
                                  coords=[component_list, time_list, space_list], 
                                  dims=['component', 'time','space'])

  ## 1d variable data
  capacityMax_1d = np.array([ [15,  15,  0, 0],
                            [np.nan] *4, 
                            [np.nan] *4, 
                          ])

  capacityMax_1d_da = xr.DataArray(capacityMax_1d, 
                              coords=[component_list, space_list], 
                              dims=['component', 'space'])

  capacityFix_1d = np.array([ [np.nan] *4, 
                           [5,  5,  5, 5],
                            [np.nan] *4, 
                          ])

  capacityFix_1d_da = xr.DataArray(capacityFix_1d, 
                              coords=[component_list, space_list], 
                              dims=['component', 'space'])

  ## 2d variable data
  capacityMax_2d = np.array([ [[np.nan] * 4 for i in range(4)], 

                        [[np.nan] * 4 for i in range(4)],

                         [[ 0,  5,  5, 5],
                          [ 5,  0,  5, 5],
                          [ 5,  5,  0, 5],
                          [ 5,  5,  5, 0]]
                        ])

  capacityMax_2d_da = xr.DataArray(capacityMax_2d, 
                              coords=[component_list, space_list, space_list], 
                              dims=['component', 'space', 'space_2'])
  
  locationalEligibility_2d = np.array([ [[np.nan] * 4 for i in range(4)], 

                        [[np.nan] * 4 for i in range(4)],

                         [[ 0,  1,  1, 1],
                          [ 0,  0,  1, 1],
                          [ 0,  0,  0, 1],
                          [ 0,  0,  0, 0]]
                        ])

  locationalEligibility_2d_da = xr.DataArray(locationalEligibility_2d, 
                              coords=[component_list, space_list, space_list], 
                              dims=['component', 'space', 'space_2'])

  test_xr = xr.Dataset({'ts_operationRateMax': operationRateMax_da, 
                        'ts_operationRateFix': operationRateFix_da,
                        '1d_capacityMax': capacityMax_1d_da, 
                        '1d_capacityFix': capacityFix_1d_da, 
                        '2d_capacityMax': capacityMax_2d_da, 
                        '2d_locationalEligibility': locationalEligibility_2d_da
                        })    
         
  test_geometries = [Polygon([(0,0), (2,0), (2,2), (0,2)]),
                    Polygon([(2,0), (4,0), (4,2), (2,2)]),
                    Polygon([(0,0), (4,0), (4,4), (0,4)]),
                    Polygon([(0,0), (1,0), (1,1), (0,1)])]   

  test_xr = spu.add_objects_to_xarray(test_xr,
                              description ='gpd_geometries',  
                              dimension_list =['space'], 
                              object_list = test_geometries)   

  return namedtuple("dict_and_xr", "sub_to_sup_region_id_dict test_xr")(sub_to_sup_region_id_dict, test_xr)    

#============================================Fixtures for RE Representation==================================================#

@pytest.fixture
def gridded_RE_data(scope="session"):
  time_steps = 10
  x_coordinates = 5
  y_coordinates = 3

  time = np.arange(time_steps)
  x_locations = [1, 2, 3, 4, 5]
  y_locations = [1, 2, 3]

  #capacity factor time series 
  capfac_xr_da = xr.DataArray(coords=[x_locations, y_locations, time], 
                              dims=['x', 'y','time'])

  capfac_xr_da.loc[[1, 2, 5], :, :] = [np.full((3, 10), 1) for x in range(3)]
  capfac_xr_da.loc[3:4, :, :] = [np.full((3, 10), 2) for x in range(2)]

  #capacities
  test_data = np.ones((x_coordinates, y_coordinates))
  capacity_xr_da = xr.DataArray(test_data, 
                              coords=[x_locations, y_locations], 
                              dims=['x', 'y'])

  test_xr_ds = xr.Dataset({'capacity': capacity_xr_da,
                          'capfac': capfac_xr_da}) 

  test_xr_ds.attrs['SRS'] = 'epsg:3035'

  return test_xr_ds


@pytest.fixture
def sample_shapefile(scope="session"):
  polygon1 = Polygon([(0,0), (4,0), (4,4), (0,4)])
  polygon2 = Polygon([(4,0), (7,0), (7,4), (4,4)])

  test_geometries = [MultiPolygon([polygon1]),
                  MultiPolygon([polygon2])] 

  df = pd.DataFrame({'region_ids': ['reg_01', 'reg_02']})

  gdf = gpd.GeoDataFrame(df, geometry=test_geometries, crs={'init': 'epsg:3035'}) 

  return gdf







