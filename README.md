# Zone-Translator

This tool is to be used for UK zones however it could be used for other geographies if the correct data inputs can be acquired. Prior to use the user must obtain the open source ONS data for LSOA zones, populations and employment figures.
These data sources can be found here:

Boundaries: https://geoportal.statistics.gov.uk/datasets/lower-layer-super-output-areas-december-2011-boundaries-generalised-clipped-bgc-ew-v3/explore    
Populations: https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/lowersuperoutputareamidyearpopulationestimates
Employment: https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datalist?filter=user_requested_data&size=50&sortBy=release_date&page=2
(Always check for the latest release of the data)

The tool will output a non weighted correspondence between the two input zones as standard. These are labelled as "zone1_to_zone2_correspondence.csv".

The tool will then determine whether the Zone 1 to Zone 2 relationship is one-to-many or many-to-many. If it is many-to-many the script will conduct a "Weighted Translation" between the two input zones.
These outputs will be named accordingly: "zone1_to_zone2_lsoa_population_weight"

The translation can be weighted by either population or employment. This is defined in the "method" variable. For example "method = lsoa_population".

## Methodology

For the non weighted correspondence the script uses a Geopandas function to intersect the zones. The overlaps are then quantified by calculating the ratio of the overlap to each zone's area.

### Example of a non weighted correspondence output

For the weighted translation the script uses Geopandas again to calculate the correspondence between the input zones and the Lower Super Output Areas (LSOAs).

The two zone-to-LSOA correspondences are then compared to one another to search for overlaps between the same LSOAs.



Each run of the tool will be logged in the master_zone_translation_log.csv which will be created in the location specified by the "save_path" variable.




## User Guide

- Download the LSOA areas, populations and employment figures. 
- Download the scripts from GitHub and installing the required pandas and Geopandas modules into your environment.
- Open the "run_zone_translation.py" script. 
- At the bottom of the script change the "main()" function's inputs.
- Inputs required are:
	zone_1_name - Name of your first zone, refer to the "master_zone_translation_log.csv" to see existing naming conventions for zones.
	zone_2_name - Name of your second zone, refer to the "master_zone_translation_log.csv" to see existing naming conventions for zones. The order of the
		      zones does not matter.
	zone_1_path - The file path to your first zone, this should match to your zone_1_name.
	zone_2_path - The file path to your second zone, this should match to your zone_2_name.
	method - This defines the weighting method you would like to apply if a weighted translation is required. Inputs available are: 'lsoa_population' and
		 'lsoa_employment'


