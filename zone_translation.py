import os
import zt_constants as ztc
import geo_utils as nf
import zone_correspondence as zc
import pandas as pd
import datetime
import csv
import sys

class ZoneTranslation:

    def __init__(self,
                 zone_1_path,
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
                 filter_slithers):
        
        self.zone_1_name = zone_1_name
        self.zone_2_name = zone_2_name
        self.zone_1_path = zone_1_path
        self.zone_2_path = zone_2_path
        self.lsoa_trans1 = lsoa_trans1
        self.lsoa_trans2 = lsoa_trans2
        self.tolerance = tolerance
        self.out_path = out_path
        self.point_handling = point_handling
        self.point_tolerance = point_tolerance
        self.point_zones_path = point_zones_path
        self.lsoa_shapefile_path = lsoa_shapefile_path
        self.lsoa_data_path = lsoa_data_path
        self.rounding = rounding
        self.filter_slithers = filter_slithers

        # Does a regular spatial correspondence between zones
        spatial_correspondence,final_zone_corr_path, zones_switch = zc.main_zone_correspondence(zone_1_path = self.zone_1_path,
                                             zone_2_path = self.zone_2_path,
                                             zone_1_name = self.zone_1_name,
                                             zone_2_name = self.zone_2_name,     
                                             tolerance = self.tolerance,
                                             out_path = self.out_path,
                                             point_handling = self.point_handling,
                                             point_tolerance = self.point_tolerance,
                                             point_zones_path = self.point_zones_path,
                                             lsoa_shapefile_path = self.lsoa_shapefile_path,
                                             lsoa_data_path =self.lsoa_data_path,
                                             rounding = self.rounding,
                                             filter_slithers = self.filter_slithers)


        distinct_zones_2_count = len(pd.unique(spatial_correspondence.iloc[: , 1]))
        
        print("Determining if Zone Translation is required.\n")
        
        #unique_values = pd.unique(spatial_correspondence.iloc[: , 3])
        #print(unique_values)
        
        if distinct_zones_2_count != len(spatial_correspondence.iloc[: , 1]):
            print("Many to Many relationship identified, Zone translation needed \n")  
            translation_needed = True
        else:
            print("One to Many relationship identified, Spatial translation is sufficient \n")
            translation_needed = False        

       
        # Switch lsoa_trans around so that the bigger area is always lsoa_trans1 this gets the order of the zone_corre out in desired order
        # If weighted translation is not needed stop the script.

        if translation_needed:
            if zones_switch:     
                if lsoa_trans1 == "":
                    try:
                        self.lsoa_trans1 = self.find_lsoa_translation(zone_2_name)
                    except:
                        print("Running Zone to LSOA Correspondence for Zone 1 \n")
                        self.lsoa_trans1 = self.run_lsoa_translation(zone_2_name)
                if lsoa_trans2 == "":
                    try:
                        self.lsoa_trans2 = self.find_lsoa_translation(zone_1_name)
                    except:
                        print("Running Zone to LSOA Correspondence for Zone 2 \n")
                        self.lsoa_trans2 = self.run_lsoa_translation(zone_1_name)
                print(f"lsoa_trans1 is taken from: {self.lsoa_trans1} \n")
                print(f"lsoa_trans2 is taken from: {self.lsoa_trans2} \n")
            else:
                if lsoa_trans1 == "":
                    try:
                        self.lsoa_trans1 = self.find_lsoa_translation(zone_1_name)
                    except:
                        print("Running Zone to LSOA Correspondence for Zone 1 \n")
                        self.lsoa_trans1 = self.run_lsoa_translation(zone_1_name)
                if lsoa_trans2 == "":
                    try:
                        self.lsoa_trans2 = self.find_lsoa_translation(zone_2_name)
                    except:
                        print("Running Zone to LSOA Correspondence for Zone 2 \n")
                        self.lsoa_trans2 = self.run_lsoa_translation(zone_2_name)
                print(f"lsoa_trans1 is taken from: {self.lsoa_trans1} \n")
                print(f"lsoa_trans2 is taken from: {self.lsoa_trans2} \n")                
        else:
            sys.exit()

        
        print(f"Does order of Zones need Switching? : {zones_switch} \n")

        
    def run_lsoa_translation(self, zone_to_translate):


        """Runs a spatial correspondence between specified zones and LSOA zones.
       
        Parameters
        ----------
        zone_to_translate : str
            Path to zone system shapefile
    
        Returns
        -------
        pd.DataFrame
        Contains correspondence values between zone and LSOA zone.
        Columns are zone_id, lsoa code, zone to lsoa match value,
        lsoa to zone match value.
        """            
        if zone_to_translate == self.zone_1_name:
            trans_shape = self.zone_1_path
            trans_name = self.zone_1_name
        elif zone_to_translate == self.zone_2_name:
            trans_shape = self.zone_2_path
            trans_name = self.zone_2_name
        
        lsoa_translation = zc.main_zone_correspondence(zone_1_path = trans_shape,
                                                       zone_2_path = ztc.ZLSOA,
                                                       zone_1_name = trans_name,
                                                       zone_2_name = 'lsoa', 
                                                       tolerance = self.tolerance,
                                                       out_path = self.out_path,
                                                       point_handling = self.point_handling,
                                                       point_tolerance = self.point_tolerance,
                                                       point_zones_path = self.point_zones_path,
                                                       lsoa_shapefile_path = self.lsoa_shapefile_path,
                                                       lsoa_data_path =self.lsoa_data_path,
                                                       rounding = self.rounding,
                                                       filter_slithers = self.filter_slithers,)[1]

        print('LSOA Translation Completed \n')
        
        return(lsoa_translation)

    def find_lsoa_translation(self,zone_name):

        """Looks for existing lsoa translations in out path location.
        If found the zone to lsoa translation will be used for the weighted
        zone translation instead of creating a new zone to lsoa translation.
        
         Parameters
         ----------
         out_path : str
             Output path
         zone_name : str
             Name of zone system
     
         Returns
         -------
         Zone to LSOA translation file path: str
             Path to Zone to LSOA translation csv file.
         """
        print("Searching for existing LSOA Translation \n")
        try:
            lsoatp = [x for x in os.listdir(self.out_path) if zone_name in x]
            lsoatp = [x for x in lsoatp if 'to_lsoa' in x]
            lsoatp =lsoatp[0]
            err_loop = 0
            while '.csv' not in lsoatp:
                print('Searching %s' % lsoatp)
                folder = lsoatp
                lsoatp = os.listdir(
                    os.path.join(self.out_path, lsoatp))
                lsoatp = [x for x in lsoatp if 'to_lsoa' in x]
                lsoatp = [x for x in lsoatp if 'dropped' not in x]
                lsoatp = os.path.join(folder, lsoatp[0])
                
                err_loop+=1
                
                if err_loop > 5:
                    raise ValueError('Lost in translations')
                    
            print('Using %s \n' % lsoatp)
        
        except:
            print("Existing LSOA Translation not found \n")
            raise ValueError('No file found')

        return os.path.join(self.out_path, lsoatp)


    def weighted_translation(self,
                             correspondence_path1,
                             correspondence_path2,
                             method,
                             start_time,
                             write=True
                             ):
        """ Runs a weighted translation using the zone 1 to LSOA correspondence
        csv file and the zone 2 to LSOA correspondence csv file. The type of
        variable to weight the translation by, such as population or 
        employment, is chosen by the method variable. 
        
         Parameters
         ----------
         zone_1_name : str
             Name of zone system
         zone_2_name : str
             Name of zone system
         correspondence_path1 : str
             Path to translation csv file
         correspondence_path2 : str
             Path to translation csv file
         method : str  
             Weighting method choice
         start_time : datetime
             Start time and date of script run
         write : bool
             Indicates if weighted translation should be exported to csv
         Returns
         -------
         weighted_translation: pd.DataFrame
             Weighted Translation between Zone 1 and Zone 2
         """
        print("Starting weighted_translation \n")
        # Init
        zone_name1 = self.zone_1_name.lower()
        zone_name2 = self.zone_2_name.lower()

        weighted_translation = nf.zone_split(
            correspondence_path1,
            correspondence_path2,
            method)

        column_list = list(weighted_translation.columns)
        
        summary_table_1 = weighted_translation.groupby(column_list[0])[column_list[2]].sum()
        summary_table_2 = weighted_translation.groupby(column_list[1])[column_list[3]].sum()
        
        under_1_zones_1 = summary_table_1[summary_table_1 < 0.999999]
        under_1_zones_2 = summary_table_2[summary_table_2 < 0.999999]
        
        if len(pd.unique(weighted_translation[column_list[0]])) == sum(summary_table_1):
            print(f'Split factors add up to 1 for {column_list[0]} \n')
        else: 
            print(f'WARNING, Split factors DO NOT add up to 1 for {column_list[0]}. CHECK TRANSLATION IS ACCURATE \n')
            print(under_1_zones_1)
            print('\n')
            
        if len(pd.unique(weighted_translation[column_list[1]])) == sum(summary_table_2):
            print(f'Split factors add up to 1 for {column_list[1]} \n')
        else: 
            print(f'WARNING, Split factors DO NOT add up to 1 for {column_list[1]}. CHECK TRANSLATION IS ACCURATE \n')
            print(under_1_zones_2)
            print('\n')
            
        if write:
            fname = "%s_%s_%s_weight.csv" % (zone_name1, zone_name2, method)
            out_path = os.path.join(self.out_path, fname)
            weighted_translation.to_csv(out_path, index=False)

            print("Copy of translation written to: %s \n" % out_path)
        
        run_time = datetime.datetime.now() - start_time
        print("Script Completed in  : ",(run_time))
        
        log_data = {
        "Run Time" : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Zone 1 name": self.zone_1_name,
        "Zone 2 name": self.zone_2_name,
        "Zone 1 shapefile": self.zone_1_path,
        "Zone 2 Shapefile": self.zone_2_path,
        "Output directory": out_path,
        "Tolerance": self.tolerance,
        "Point handling": self.point_handling,
        "Point list": self.point_zones_path,
        "Point tolerance": self.point_tolerance,
        "LSOA data": self.lsoa_data_path,
        "LSOA shapefile": self.lsoa_shapefile_path,
        "Rounding": self.rounding,
        "filter_slithers" : self.filter_slithers,
        "type" : "weighted_translation",
        "method" : method,
        "run_time" : run_time
        }
    
        # Update master log spreadsheet with run parameter
        # convert dict values to list
        
        list_of_elem = list(log_data.values())
        try:
            with open(os.path.join(self.out_path, 'master_zone_translation_log.csv'), 'a+', newline='') as write_obj:
                
                # Create a writer object from csv module
                csv_writer = csv.writer(write_obj)
                # Add contents of list as last row in the csv file
                csv_writer.writerow(list_of_elem)
        except Exception as error:
            print("Failed to add to Master Log: " + str(error))

        return weighted_translation
