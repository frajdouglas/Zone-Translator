import zone_translation as zt
import datetime
import pandas as pd
pd.set_option('display.max_columns', 50)

def main(zone_1_name,zone_1_path,zone_2_name,zone_2_path,method):

    # START TIMER
    start_time = datetime.datetime.now()
    
    # Settings and file locations should be set here, these will be the attributes in the ZoneTranslation Object  
    lsoa_trans1 = "" 
    lsoa_trans2 = ""
    tolerance = 0.98
    out_path = 'I:/Data/Zone Translations/'
    point_handling = False
    point_tolerance = 0.95
    point_zones_path = ""
    lsoa_shapefile_path = ""
    lsoa_data_path = ""
    rounding = True
    filter_slithers = True
       
    # translation object instantiation with all settings set at top of script. 
    # If no lsoa_trans variable is set then object instantiation will go find this and failing that will create a new zone to lsoa correspondence file.
    translation = zt.ZoneTranslation(zone_1_path,
                                    zone_2_path,
                                    zone_1_name,
                                    zone_2_name,
                                    lsoa_trans1,
                                    lsoa_trans2,
                                    tolerance,
                                    out_path,
                                    point_handling,
                                    point_tolerance,
                                    point_zones_path,
                                    lsoa_shapefile_path,
                                    lsoa_data_path,
                                    rounding,
                                    filter_slithers)
        
    
    # Translation object is passed to weighted translation function which will add lsoa populations to the zone to lsoa correspondences.
    # It will then merge these two tables and calculate the weighted translation between them. The method varible determines which value is joined to lsoas,
    # If it has been determined a spatial translation is sufficient then the weighted translation is skipped
    
    print(f"Zone 1 to LSOA translation path : {translation.lsoa_trans1} \n")
    print(f"Zone 2 to LSOA translation path : {translation.lsoa_trans2} \n")
    translation.weighted_translation(
        translation.lsoa_trans1,
        translation.lsoa_trans2,
        method,
        start_time,
        write=True)

# Define zones to translate

if __name__ == '__main__':
    main(,,,,'lsoa_population')
    


   