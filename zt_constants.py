import os

SHP_PATH = ''

# Existing Shapefiles

ZLSOA = os.path.join(SHP_PATH, 'UK LSOA and Data Zone Clipped 2011/uk_ew_lsoa_s_dz.shp')
ZLAD20 = os.path.join(SHP_PATH, 'Local_Authority_Districts_(December_2020)_UK_BFC.shp')


# LSOA/MSOA Populations, employment and other variables
LSOAPOP18 = os.path.join(SHP_PATH, 'lsoa__populations_2018.csv')
LSOAEMP18 = os.path.join(SHP_PATH, 'lsoa_employment_2018.csv')

# CRS System for osgb
OSGB_CRS = {'proj': 'tmerc',
            'lat_0': 49,
            'lon_0': -2,
            'k': 0.9996012717,
            'x_0': 400000,
            'y_0': -100000,
            'datum': 'OSGB36',
            'units': 'm',
            'no_defs': True}
