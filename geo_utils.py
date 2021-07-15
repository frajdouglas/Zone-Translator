import pandas as pd
import zt_constants as ztc

def var_apply(area_correspondence_path, var_path):
    """ Joins chosen method variable to Zone to LSOA correspondence table on
        LSOA code.
        
         Parameters
         ----------
         area_correspondence_path : str
             Path to correspondence csv file
         var_path : str
             Path to variable csv file
         correspondence_path1 : str
             Path to Zone 1 correspondence csv file
         correspondence_path2 : str
             Path to Zone 2 correspondence csv file
         method : str  
             Weighting method choice
         start_time : datetime
             Start time and date of script run
         write : bool
             Indicates if weighted translation should be exported to csv
         Returns
         -------
         area_correspondence_var: pd.DataFrame
             Zone to LSOA correspondence code with attached variable values.
    """
    # Read in the variables to join to the lsoa to zone translation
    
    zone_variables = pd.read_csv(var_path)
    zone_variables['var'] = zone_variables['var'].astype(float)
 
    # Read in the lsoa to zone correspondence
    
    area_correspondence = pd.read_csv(area_correspondence_path, index_col = False)

    # To handle old existing LSOA Translations which include the overlap type column we need to remove this as the new format does not include this. Once translations are recreated this will no longer be an issue
    area_correspondence = area_correspondence.drop(['overlap_type'], axis=1, errors='ignore')

    # Merge var zones onto area translation file. NEEDS UPDATING TO HANDLE MSOA JOINS
    area_correspondence_var = pd.merge(area_correspondence, zone_variables, how = 'outer', left_on = 'lsoa_zone_id', right_on = 'objectid') # need to fix these column assigments
    # Count lsoas/msoas which have not joined to translation indicating they do not intersect with lsoa/msoa zones.
    missing_lsoas = area_correspondence_var['lsoa_zone_id'].isna().sum()
    
    print(f"{missing_lsoas} lsoa/msoa zones are not intersected by zones")
    
    area_correspondence_var = area_correspondence_var.drop(['objectid'], axis=1)
    
    area_correspondence_var.dropna(subset=['lsoa_zone_id'])
    
    # 0 = major zone ID, 1 = minor zone ID, 2 = major to minor nest factor, 3 = minor to major nest factor 

    #Multiply var by the minor to major overlap
    area_correspondence_var['var'] = (area_correspondence_var.iloc[:, 3] * area_correspondence_var['var'])
    print("Variable added to LSOA Zone Translation")

    return(area_correspondence_var)

def zone_split(area_correspondence_path1, area_correspondence_path2 = None, method = 'lsoa_population'): 
    """ Joins chosen method variable to Zone to LSOA correspondence table on
        LSOA code using var_apply function then calculates weighted
        translation between Zone 1 and Zone 2.
        
         Parameters
         ----------
         area_correspondence_path1 : str
             Path to Zone 1 to LSOA correspondence csv file
         area_correspondence_path2 : str
             Path to Zone 2 to LSOA correspondence csv file
         method : str  
             Weighting method choice

        Returns
         -------
         weighted_translation: pd.DataFrame
             Zone 1 to Zone 2 weighted translation using defined method
    """
    if method == 'lsoa_population':
        var_path = ztc.LSOAPOP18
        popCol = 'lsoa'
    elif method == 'msoa_population':
        var_path = ztc.MSOAPOP11
        popCol = 'msoa'
    elif method == 'lsoa_employment':
        var_path = ztc.LSOAEMP18
        popCol = 'lsoa'
    elif method == 'lsoa_commute':
        var_path = ztc.LSOACOM
        popCol = 'lsoa'
    elif method == 'lsoa_business':
        var_path = ztc.LSOABUS
        popCol = 'lsoa'
    elif method == 'lsoa_other':
        var_path = ztc.LSOAOTH
        popCol = 'lsoa'
    else:
        var_path = method
  
    if area_correspondence_path2 == None:
        area_correspondence_var = var_apply(area_correspondence_path1, var_path)
        atname = area_correspondence_var.columns[0].replace('_zone_id', '')
        area_correspondence_names = [atname, popCol]
        ats = [area_correspondence_var, area_correspondence_var]
    else:
        area_correspondence_list = [area_correspondence_path1, area_correspondence_path2]
        ats = [0, 0]
        area_correspondence_names = [0, 0]
        i = 0
        for at in area_correspondence_list:
            area_correspondence_var = var_apply(at, var_path)            
            atname = area_correspondence_var.columns[0].replace('_zone_id', '')
            area_correspondence_names[i] = atname
            ats[i] = area_correspondence_var
            i = i+1
            
        # Outer Join to keep var zones which do not intersect with any zone
        area_correspondence_var = pd.merge(ats[0], ats[1], how = 'outer', left_on = ['lsoa11cd', 'lsoa_zone_id'], right_on = ['lsoa11cd', 'lsoa_zone_id'])
        min_var = area_correspondence_var
        min_var['var'] = min_var[['var_x', 'var_y']].min(axis=1)
        min_var = min_var.drop(['var_x', 'var_y'], axis=1)

    # Loop to get sums from newly adjusted totals
     # the atsum variables stores the var total for each zone area. one table for zone 1 totals and another for zone 2 totals
    area_correspondence_sums = [0]*len(area_correspondence_names)
    j = 0
    for at in area_correspondence_names:
        # pass zone_names here
        zone_col = at + '_zone_id'
        # group by the zone code
        area_correspondence_sum = area_correspondence_var.groupby(area_correspondence_var.loc[:,zone_col])['var'].agg('sum').reset_index()
        # change column name to zone_var
        area_correspondence_sum = area_correspondence_sum.rename(columns = {area_correspondence_sum.columns[1] : area_correspondence_names[j] + '_value'})
        del(zone_col)
        area_correspondence_sums[j] = area_correspondence_sum
        j = j+1
       
    ### This part here is what determines the "overlap_var" it is a groupby on the zone1 then 2
    var_merge_step = area_correspondence_var.groupby([area_correspondence_var.loc[:,area_correspondence_names[0]+'_zone_id'], area_correspondence_var.loc[:,area_correspondence_names[1]+'_zone_id']])['var'].sum().reset_index()
    var_merge_step = var_merge_step.rename(columns = {var_merge_step.columns[2] : 'overlap_value'})

    ### Merges the individual zone totals onto the zone1 zone 2 overlap var table
    weighted_translation = pd.merge(var_merge_step, area_correspondence_sums[0], how = 'inner', left_on = area_correspondence_names[0]+'_zone_id', right_on = area_correspondence_names[0] + '_zone_id')  
    weighted_translation = pd.merge(weighted_translation, area_correspondence_sums[1], how = 'inner', left_on = area_correspondence_names[1]+'_zone_id' , right_on = area_correspondence_names[1]+'_zone_id')

    # Name split factors
    weighted_translation[area_correspondence_names[0]+'_to_'+area_correspondence_names[1]] = weighted_translation['overlap_value']/weighted_translation[area_correspondence_names[0]+'_value']
    weighted_translation[area_correspondence_names[1]+'_to_'+area_correspondence_names[0]] = weighted_translation['overlap_value']/weighted_translation[area_correspondence_names[1]+'_value']

    print(weighted_translation)
    
    # Drop non essential columns
    # Zone_correspondence should be in configuration: 0 'zone1ID', 1 'zone2ID', 2 'overlap_population', 3 'zone1_population', 4 'zone2_population', 5 'overlap_zone1_factor', 6 'overlap_zone2_factor'
    # All calls to iloc are based on this so if it's not right these won't work
    weighted_translation.drop(weighted_translation.columns[[2,3,4]], axis = 1, inplace = True)

    return weighted_translation


