import geopandas as gpd
import pandas as pd
import csv
import datetime
import os
import sys

def read_zone_shapefiles(zone_1_path, zone_2_path, zone_1_name, zone_2_name):
    """Reads in zone system shapefiles, sets zone id and area column names,
    sets to same crs.

    If the provided shapefiles don't contain CRS information then they're assumed to
    be "EPSG:27700".
    Parameters
    ----------
    zone_1_path : str
        Path to first zone system shapefile
    zone_2_path : str
        Path to second zone system shapefile
    zone_1_name : str
        Name of first zone system
    zone_2_name : str
        Name of second zone system

    Returns
    -------
    List[GeoDataFrame, GeoDataFrame], List[str, str]
        List of zone 1 and zone 2 GeoDataFrames and a list with the names of
        the zones
    """
    print("Reading in zone shapefiles for zone correspondence \n")
    
    # zone column lookups
    EXISTING_NAME_LOOKUP = {"lsoa11cd" : "zone_id", "lad20cd" : "zone_id", "msoa11cd" : "zone_id"}
    LOOKUP = {"zoneid" : "zone_id","unique_id": "zone_id","uniqueid": "zone_id","object_id": "zone_id","objectid": "zone_id","id": "zone_id","sector_id" : "zone_id", "id" : "zone_id","fid" : "zone_id", "sectorid" : "zone_id", "sector_id" : "zone_id", "DataZone" : "zone_id"}
    
    
    # create geodataframes from zone shapefiles
    zone_1 = gpd.read_file(zone_1_path)
    zone_2 = gpd.read_file(zone_2_path)
    
    zone_1 = zone_1.dropna(axis=1,how='all')
    zone_2 = zone_2.dropna(axis=1,how='all')
    
    print(f"Count of {zone_2_name} zones: " + str(zone_2.iloc[:, 0].count())+'\n')
    print(f"Count of {zone_1_name} zones: " + str(zone_1.iloc[:, 0].count())+'\n')
 
    # Put larger zones first
    
    zone_1['area'] = zone_1.area
    zone_1 = zone_1.dropna(subset=['area'])
    zone_2['area'] = zone_2.area
    zone_2 = zone_2.dropna(subset=['area'])
    
    if(sum(zone_1['area'])/len(zone_1) > sum(zone_2['area'])/len(zone_2)):
        # Assign to maj/min
        major_zone = zone_1.copy()
        major_zone_name = zone_1_name
        minor_zone = zone_2.copy()
        minor_zone_name = zone_2_name
        zones_switch = False

    elif(sum(zone_1.area)/len(zone_1) < sum(zone_2.area)/len(zone_2)):
        # Assign to maj/min
        major_zone = zone_2.copy()
        major_zone_name = zone_2_name
        minor_zone = zone_1.copy()
        minor_zone_name = zone_1_name
        zones_switch = True
        

    del zone_1, zone_2
    del major_zone['area'], minor_zone['area']
    
    # create lists to deal with zones and names. Put larger zones first
    zone_names = [major_zone_name, minor_zone_name]
    zone_list = [major_zone, minor_zone]

    #LOWER all column names
    major_zone.columns = major_zone.columns.str.lower()
    minor_zone.columns = minor_zone.columns.str.lower()

    # rename zone number columns, add area column, complete crs data
    for i in range(2):
        if "lsoa11cd" in zone_list[i].columns or "lad20cd" in zone_list[i].columns or "msoa11cd" in zone_list[i].columns:
            # converts lsoacd to standard "zone_id" name to ensure it works in next functions
            zone_list[i] = zone_list[i].rename(columns=EXISTING_NAME_LOOKUP)
        else:
            zone_list[i] = zone_list[i].rename(columns=LOOKUP)

        if "zone_id" not in zone_list[i].columns:
            print("no lookup for this zone system, need to know column names \n")
            sys.exit()

        zone_list[i] = zone_list[i].rename(
            columns={"zone_id": f"{zone_names[i]}_zone_id"}
        )
        zone_list[i][f"{zone_names[i]}_area"] = zone_list[i].area

        # Set zone projection to ESPG:27700 if not already
        if not zone_list[i].crs:
            zone_list[i].crs = "EPSG:27700"
    
    return zone_list, zone_names, zones_switch


def read_lsoa_data(lsoa_shapefile_path, lsoa_data_path):
    # FRASER 23/6/21 - Required for Point Handling which is not currently supported in tool.
    """Reads in LSOA shapefile and data, renames columns, combines shapefile
    with data.

    Parameters
    ----------
    lsoa_shapefile_path : str
        Path to LSOA zones shapefile, which is assumed to have a column named
        "LSOA11CD" with zone IDs.
    lsoa_data_path : str
        Path to desired LSOA data to perform point zone handling with. This
        file is assumed to be a csv with columns named "lsoa11cd" and "var".

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with LSOA shapefile data and selected data in var column
    """
    # read in and combine LSOA data
    lsoa_zones = gpd.read_file(lsoa_shapefile_path)
    lsoa_data = gpd.read_file(lsoa_data_path)
    lsoa_data = lsoa_data.rename(columns={"lsoa11cd": "lsoa_zone_id"})
    lsoa_zones = lsoa_zones.rename(columns={"LSOA11CD": "lsoa_zone_id"})
    lsoa_data = lsoa_data[["lsoa_zone_id", "var"]]
    lsoa_data["var"] = lsoa_data["var"].astype(float)
    lsoa_zones_var = lsoa_zones.merge(
        lsoa_data, how="inner", left_on="lsoa_zone_id", right_on="lsoa_zone_id"
    )
    lsoa_zones_var["lsoa_area"] = lsoa_zones_var.area

    return lsoa_zones_var


def spatial_zone_correspondence(zone_list, zone_names):
    """Finds the spatial zone corrrespondence through calculating adjustment
    factors with areas only. LSOA data is assumed to be in a column named
    "var".

    Parameters
    ----------
    zone_list : List[GeoDataFrame, GeoDataFrame]
        List of zone 1 and zone 2 GeoDataFrames
    zone_names : List[str, str]
        List of zone names

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with 4 columns: zone 1 IDs, zone 2 IDs, zone 1 to zone 2
        adjustment factor and zone 2 to zone 1 adjustment factor
    """
    
    # create geodataframe for intersection of zones
    zone_overlay = gpd.overlay(
        zone_list[0], zone_list[1], how="intersection",keep_geom_type=False
    ).reset_index()
    zone_overlay.loc[:, "intersection_area"] = zone_overlay.area    
   
    # columns to include in spatial correspondence
    column_list = [f"{zone_names[0]}_zone_id", f"{zone_names[1]}_zone_id"]

    # create geodataframe with spatial adjusted factors
    spatial_correspondence = zone_overlay.loc[:,column_list]

#FRASER EDIT 23/6/21 - Suspect this is for point handling functionality

# =============================================================================
#     # var is important data to include in lsoa case
#     if "var" in zone_overlay.columns:
#         column_list.append("var")
# =============================================================================

    # create geodataframe with spatial adjusted factors
    spatial_correspondence.loc[:, f"{zone_names[0]}_to_{zone_names[1]}"] = (
        zone_overlay.loc[:, "intersection_area"]
        / zone_overlay.loc[:, f"{zone_names[0]}_area"]
    )
    spatial_correspondence.loc[:, f"{zone_names[1]}_to_{zone_names[0]}"] = (
        zone_overlay.loc[:, "intersection_area"]
        / zone_overlay.loc[:, f"{zone_names[1]}_area"]
    )
    
    print('Unfiltered Spatial Correspondence completed\n')
    
    return spatial_correspondence


def find_slithers(spatial_correspondence, zone_names, tolerance):
    """Finds overlap areas between zones which are very small slithers,
    filters them out of the spatial zone correspondence GeoDataFrame, and
    returns the filtered zone correspondence as well as the GeoDataFrame with
    only the slithers.

    Parameters
    ----------
    spatial_correspondence : GeoDataFrame
        Spatial zone correspondence between zone 1 and zone 2 produced with
        spatial_zone_correspondence
    zone_names: List[str, str]
        List of the zone names that the spatial correspondence was performed
        between
    tolerance : float
        User-defined tolerance for filtering out slithers, must be a float
        between 0 and 1, recommended value is 0.98

    Returns
    -------
    GeoDataFrame, GeoDataFrame
        slithers GeoDataFrame with all the small zone overlaps, and
        no_slithers the zone correspondence GeoDataFrame with these zones
        filtered out
    """
    print("Finding Slithers\n")
    
    slither_filter = (
        spatial_correspondence[f"{zone_names[0]}_to_{zone_names[1]}"] < (1 - tolerance)
    ) & (
        spatial_correspondence[f"{zone_names[1]}_to_{zone_names[0]}"] < (1 - tolerance)
    )
    slithers = spatial_correspondence.loc[slither_filter]
    no_slithers = spatial_correspondence.loc[~slither_filter]
    
    return slithers, no_slithers


def remove_minor_point_zone_mappings(point_zone_correspondence, zone_names):
    # FRASER 23/6/21 - Required for Point Handling which is not currently supported in tool.
    """Find point zones in zone 2 which map to more than one original zone id.
    Assign all the mapping to the original zone id which contains the largest
    proportion of the point zone.

    Parameters
    ----------
    point_zone_correspondence : gpd.GeoDataFrame
        Spatial correspondence for only point zones
    zone_names : List[str, str]
        Names of zone systems

    Returns
    -------
    gpd.GeoDataFrame
        Point zone correspondence where every zone 2 point zone is mapped to a
        single point 1 zone
    """
    # check for any point zones that map to more than one original zone
    duplicated_point_mappings = point_zone_correspondence.loc[
        point_zone_correspondence[f"{zone_names[1]}_zone_id"].duplicated(keep=False)
    ]

    # find original zone ids that receive largest proportion of duplicated
    # point zones
    zone_2_to_orig_max_factors = (
        duplicated_point_mappings[
            [f"{zone_names[1]}_zone_id", f"{zone_names[1]}_to_{zone_names[0]}"]
        ]
        .groupby(f"{zone_names[1]}_zone_id")
        .max(f"{zone_names[1]}_to_{zone_names[0]}")
    )

    # filter out original zones that receive lesser proportion of duplicated
    # zones
    lesser_zones_cond = (
        duplicated_point_mappings[f"{zone_names[1]}_zone_id"].isin(
            zone_2_to_orig_max_factors.index
        )
    ) & ~(
        duplicated_point_mappings[f"{zone_names[1]}_to_{zone_names[0]}"].isin(
            zone_2_to_orig_max_factors[f"{zone_names[1]}_to_{zone_names[0]}"]
        )
    )

    zones_to_remove = duplicated_point_mappings.loc[lesser_zones_cond]

    point_zone_correspondence = point_zone_correspondence.loc[
        ~point_zone_correspondence.index.isin(zones_to_remove.index)
    ]

    return point_zone_correspondence


def point_zone_filter(
    spatial_correspondence_no_slithers,
    point_tolerance,
    point_zones_path,
    zone_list,
    zone_names,
    lsoa_shapefile_path,
    lsoa_data_path,
    tolerance,
):
    
    # FRASER 23/6/21 - Required for Point Handling which is not currently supported in tool.
    
    """Finds zone system 2 point and associated zones (sharing a zone system 1
     zone), reads in LSOA data, computes intersection, filters out slithers,
     makes sure each point zone is the only one associated with that LSOA.
     Returns var data for zone 2 zones as dataframes with zone ids as indices,
     var as column.

     Parameters
     ----------
     spatial_correspondence_no_slithers : GeoDataFrame
         Spatial zone correspondence between zone systems 1 and 2, produced
         with spatial_zone_correspondence with the small overlaps filtered out
         using find_slithers.
     point_tolerance : float, optional
         Tolerance level for filtering out point zones, a number between 0 and
         1, defaults to 0.95
     point_zones : str, optional
         Path to csv file with list of point zones with column name zone_id, defaults to ""
     zone_list : List[GeoDataFrame, GeoDataFrame]
         List containing zone 1 and zone 2 GeoDataFrames.
     zone_names : List[str, str]
         List containing zone 1 and zone 2 names.
     lsoa_shapefile_path : str
         Path to LSOA shapefile (or the shapefile associated with the data to
         be used in point zone handling). Zone ID column must be called
         LSOA11CD.
     lsoa_data_path : str
         Path to csv file containing LSOA ID column as lsoa11cd and desired
         data in var column.

     Returns
     -------
     gpd.GeoDataFrame
        LSOA data for zones in zone 2 that map to the same zone 1 zone as point zones.
     gpd.GeoDataFrame
        LSOA data for point zones.
     pd.DataFrame
        Contains information on these zones, their zone 1 zone ID, zone 2 zone ID, zone
        type (point or non-point), correspondence type (LSOA or spatial) and any notes.
    gpd.GeoDataFrame
        The spatial correspondence initially input, but with point-affected zones filtered out.
    """
    # if point zone list given, read in and use to find point zone correspondence
    print(point_zones_path)
    if point_zones_path != "":
        try:
            point_list = pd.read_csv(point_zones_path, usecols=["zone_id"])
            #FRASER EDIT
            print(point_list)
        except ValueError as e:
            loc = str(e).find("columns expected")
            raise ValueError(f"Point zones file, {str(e)[loc:]}") from e
        zone_2_point_zone_filter = spatial_correspondence_no_slithers[
            f"{zone_names[1]}_zone_id"
        ].isin(point_list.zone_id)
    # if no point zone list given, find point zones with point tolerance
    else:
        zone_2_point_zone_filter = (
            spatial_correspondence_no_slithers[f"{zone_names[1]}_to_{zone_names[0]}"]
            > point_tolerance
        ) & (
            spatial_correspondence_no_slithers[f"{zone_names[0]}_to_{zone_names[1]}"]
            < (1 - point_tolerance)
        )

    zone_2_point_zones_correspondence = spatial_correspondence_no_slithers.loc[
        zone_2_point_zone_filter
    ]

    # remove point zones from spatial correspondence
    spatial_corr_no_slithers_no_pts = spatial_correspondence_no_slithers.loc[
        ~zone_2_point_zone_filter
    ]

    # filter out duplicated point zone mappings and assign to zone with most
    # of point zone
    zone_2_point_zones_correspondence = remove_minor_point_zone_mappings(
        zone_2_point_zones_correspondence, zone_names
    )

    # find all zones in zone 2 that share an original zone 1 with a point zone
    # as these are the zones that need non-spatial handling
    zone_2_point_zone_sharing_filter = spatial_corr_no_slithers_no_pts[
        f"{zone_names[0]}_zone_id"
    ].isin(zone_2_point_zones_correspondence[f"{zone_names[0]}_zone_id"])

    zone_2_pt_affected_zone_corr = spatial_corr_no_slithers_no_pts.loc[
        zone_2_point_zone_sharing_filter
    ]

    # combine point and point affected zone correspondences into the
    # non-spatial correspondence
    non_spatial_corr = pd.concat(
        [zone_2_point_zones_correspondence, zone_2_pt_affected_zone_corr]
    )

    # create dataframe to track point zone data
    point_zones_information = non_spatial_corr[
        [f"{zone_names[0]}_zone_id", f"{zone_names[1]}_zone_id"]
    ]
    point_zones_information.loc[:, "correspondence"] = "LSOA"
    point_zones_information.loc[:, "zone_type"] = "non-point"
    point_zones_information.loc[
        point_zones_information[f"{zone_names[1]}_zone_id"].isin(
            zone_2_point_zones_correspondence[f"{zone_names[1]}_zone_id"]
        ),
        "zone_type",
    ] = "point"
    point_zones_information.loc[:, "notes"] = ""

    point_zones_information = point_zones_information.sort_values(
        by=[f"{zone_names[0]}_zone_id"]
    )

    # read in lsoa data
    lsoa_zone_data = read_lsoa_data(lsoa_shapefile_path, lsoa_data_path)

    # get geodataframe of point zones and point-affected zones
    pt_adjacent_zones = zone_list[1].loc[
        zone_list[1][f"{zone_names[1]}_zone_id"].isin(
            non_spatial_corr[f"{zone_names[1]}_zone_id"]
        )
    ]

    # perform zone correspondence between LSOA zones and zones to be handled
    # non-spatially
    lsoa_zone_2_list = [lsoa_zone_data, pt_adjacent_zones]
    lsoa_zone_2_names = ["lsoa", zone_names[1]]
    lsoa_zone_2_correspondence = spatial_zone_correspondence(
        lsoa_zone_2_list, lsoa_zone_2_names
    )

    # filter out slithers from this correspondence
    lsoa_zone_2_corr_slithers, lsoa_zone_2_corr_no_slithers = find_slithers(
        lsoa_zone_2_correspondence, lsoa_zone_2_names, tolerance
    )

    # separate correspondence for point zones and non-point zones
    point_filter = lsoa_zone_2_corr_no_slithers[f"{zone_names[1]}_zone_id"].isin(
        zone_2_point_zones_correspondence[f"{zone_names[1]}_zone_id"]
    )

    lsoa_zone_2_point_corr = lsoa_zone_2_corr_no_slithers.loc[point_filter]

    lsoa_zone_2_non_point_corr = lsoa_zone_2_corr_no_slithers.loc[~point_filter]

    # filter out duplicated point zone mappings and assign to zone with most
    # of point zone
    lsoa_zone_2_point_corr = remove_minor_point_zone_mappings(
        lsoa_zone_2_point_corr, lsoa_zone_2_names
    )

    # check that all zones mapping to LSOAs associated with a point zone map
    # to other zones
    # if they don't, that means a large zone is in the same LSOA as a point zone
    # so the correspondence shall have to remain spatial

    # find non-point zones mapped to only one LSOA
    lsoa_non_point_single_mapping = lsoa_zone_2_non_point_corr.loc[
        ~lsoa_zone_2_non_point_corr[f"{zone_names[1]}_zone_id"].duplicated(keep=False)
    ]

    if not lsoa_non_point_single_mapping.empty:
        # remove zones from lsoa correspondences
        zones_to_remove = lsoa_non_point_single_mapping.loc[
            lsoa_non_point_single_mapping["lsoa_zone_id"].isin(
                lsoa_zone_2_point_corr["lsoa_zone_id"]
            )
        ]
        lsoa_zone_2_non_point_corr = lsoa_zone_2_non_point_corr.loc[
            ~lsoa_zone_2_non_point_corr["lsoa_zone_id"].isin(
                zones_to_remove["lsoa_zone_id"]
            )
        ]
        lsoa_zone_2_point_corr = lsoa_zone_2_point_corr.loc[
            ~lsoa_zone_2_point_corr["lsoa_zone_id"].isin(
                zones_to_remove["lsoa_zone_id"]
            )
        ]

        # add zones back to spatial correspondence
        zone_corr_back_to_spatial = non_spatial_corr.loc[
            non_spatial_corr[f"{zone_names[1]}_zone_id"].isin(
                zones_to_remove[f"{zone_names[1]}_zone_id"]
            )
        ]

        spatial_corr_no_slithers_no_pts = pd.concat(
            [spatial_corr_no_slithers_no_pts, zone_corr_back_to_spatial]
        )

        # add this information to point zones info dataframe
        removed_zones_filter = point_zones_information[f"{zone_names[1]}_zone_id"].isin(
            zones_to_remove[f"{zone_names[1]}_zone_id"]
        )
        point_zones_information.loc[removed_zones_filter, "correspondence"] = "spatial"
        point_zones_information.loc[
            removed_zones_filter, "notes"
        ] = f"{zone_names[1]} zone and point zone share single LSOA"

    # filter out LSOAs mapped to point zones to avoid overcounting var data
    point_zone_lsoa_filter = ~lsoa_zone_2_non_point_corr["lsoa_zone_id"].isin(
        lsoa_zone_2_point_corr["lsoa_zone_id"]
    )
    lsoa_zone_2_non_point_corr = lsoa_zone_2_non_point_corr.loc[point_zone_lsoa_filter]

    # group LSOA var data per zone 2 zone
    non_point_zone_2_var = (
        lsoa_zone_2_non_point_corr[[f"{zone_names[1]}_zone_id", "var"]]
        .groupby(f"{zone_names[1]}_zone_id")
        .sum()
    )
    point_zone_2_var = (
        lsoa_zone_2_point_corr[[f"{zone_names[1]}_zone_id", "var"]]
        .groupby(f"{zone_names[1]}_zone_id")
        .sum()
    )

    return (
        non_point_zone_2_var,
        point_zone_2_var,
        point_zones_information,
        spatial_corr_no_slithers_no_pts,
    )


def point_zone_handling(
    spatial_correspondence_no_slithers,
    point_tolerance,
    point_zones_path,
    zone_list,
    zone_names,
    lsoa_shapefile_path,
    lsoa_data_path,
    tolerance,
):
    
    # FRASER 23/6/21 - Required for Point Handling which is not currently supported in tool.
    
    """Performs zone correspondence non-spatially for point and point-affected
    zones, with LSOA data instead. Point-affected zones are zones in zone 2
    which share a zone 1 zone with a point zone.

    Parameters
    ----------
    spatial_correspondence_no_slithers : gpd.GeoDataFrame
        Spatial zone correspondence GeoDataFrame produced with
        spatial_zone_correspondence, with slithers filtered out using
        find_slithers
    point_tolerance : float
        Tolerance to find point zones, must be between 0.0 and 1.0, where
        point zones are defined as having zone_1_to_zone_2 < 1 -
        point_tolerance & zone_2_to_zone_1 > point_tolerance.
    point_zones : str, optional
        Path to csv file with list of point zones with column name zone_id, defaults to ""
    zone_list : List[gpd.GeoDataFrame, gpd.GeoDataFrame]
        Zone 1 and zone 2 GeoDataFrames from shapefiles.
    zone_names : List[str, str]
        Zone 1 and zone 2 names.
    lsoa_shapefile_path : str
        Path to LSOA shapefile (or the shapefile associated with the data to
        be used in point zone handling). Zone ID column must be called
        LSOA11CD.
    lsoa_data_path : str
        Path to csv file containing LSOA ID column as lsoa11cd and desired
        data in var column.
    tolerance : float
        Tolerance to find point zones by, where a point zone is defined as
        having zone_1_to_zone_2 < 1 - point_tolerance & zone_2_to_zone_1 >
        point_tolerance, by default 0.95

    Returns
    -------
    pd.DataFrame
        DataFrame is the new zone correspondence with point-handling,
        with 3 columns, zone 1 zone id, zone 2 zone id and zone 1 to zone 2
        adjustment factor.
    pd.DataFrame
        DataFrame is the point zone information DataFrame for the log
        file.
    """

    
    # get zone 2 point and non-point zone data
    (
        non_point_zone_2_var,
        point_zone_2_var,
        point_zones_info,
        spatial_corr_no_pts,
    ) = point_zone_filter(
        spatial_correspondence_no_slithers,
        point_tolerance,
        point_zones_path,
        zone_list,
        zone_names,
        lsoa_shapefile_path,
        lsoa_data_path,
        tolerance,
    )

    # get spatial correspondence data for point zones and point-adjacent zones
    point_zone_corr_filter = spatial_correspondence_no_slithers[
        f"{zone_names[1]}_zone_id"
    ].isin(point_zone_2_var.index)
    non_point_zone_corr_filter = spatial_correspondence_no_slithers[
        f"{zone_names[1]}_zone_id"
    ].isin(non_point_zone_2_var.index)

    spatial_corr_pt_adjacent_zones = spatial_correspondence_no_slithers.loc[
        point_zone_corr_filter | non_point_zone_corr_filter
    ]

    # combine var data for point and non-point zones
    var_pt_adjacent_zones = pd.concat([point_zone_2_var, non_point_zone_2_var])

    all_pt_adjacent_data = spatial_corr_pt_adjacent_zones.merge(
        var_pt_adjacent_zones,
        how="inner",
        left_on=f"{zone_names[1]}_zone_id",
        right_on=var_pt_adjacent_zones.index,
    )

    # get sum of spatial adjustment factors and var data per GBFM zone
    sum_data = (
        all_pt_adjacent_data[
            [f"{zone_names[0]}_zone_id", f"{zone_names[0]}_to_{zone_names[1]}", "var"]
        ]
        .groupby(f"{zone_names[0]}_zone_id")
        .sum()
    )

    sum_data = sum_data.rename(
        columns={
            f"{zone_names[0]}_to_{zone_names[1]}": f"{zone_names[0]}_to_{zone_names[1]}_sum",
            "var": "var_sum",
        }
    )

    all_pt_adjacent_data_merged = all_pt_adjacent_data.merge(
        sum_data,
        how="inner",
        left_on=f"{zone_names[0]}_zone_id",
        right_on=sum_data.index,
    )

    # get new zone 1 to zone 2 correspondence according to

    lsoa_zone_corr = all_pt_adjacent_data_merged[
        [f"{zone_names[0]}_zone_id", f"{zone_names[1]}_zone_id"]
    ]

    lsoa_zone_corr.loc[:, f"{zone_names[0]}_to_{zone_names[1]}"] = (
        all_pt_adjacent_data_merged.loc[:, f"{zone_names[0]}_to_{zone_names[1]}_sum"]
        * all_pt_adjacent_data_merged.loc[:, "var"]
        / all_pt_adjacent_data_merged.loc[:, "var_sum"]
    )

    # filter out all zones in lsoa zone correpsondence from the spatial correspondence
    spatial_corr = spatial_corr_no_pts.loc[
        ~spatial_corr_no_pts[f"{zone_names[1]}_zone_id"].isin(
            lsoa_zone_corr[f"{zone_names[1]}_zone_id"]
        )
    ]

    # combine lsoa and spatial data
    spatial_corr = spatial_corr[
        [
            f"{zone_names[0]}_zone_id",
            f"{zone_names[1]}_zone_id",
            f"{zone_names[0]}_to_{zone_names[1]}",
        ]
    ]
    new_zone_corr = pd.concat([spatial_corr, lsoa_zone_corr]).sort_values(
        by=[f"{zone_names[0]}_zone_id"]
    )

    return new_zone_corr, point_zones_info


def round_zone_correspondence(zone_corr_no_slithers, zone_names):
    """Changes zone_1_to_zone_2 adjustment factors such that they sum to 1 for
    every zone in zone 1.

    Parameters
    ----------
    zone_corr_no_slithers : pd.DataFrame
        3 column (zone 1 id, zone 2 id, zone 1 to zone 2) zone correspondence
        DataFrame, with slithers filtered out
    zone_names : List[str, str]
        List of zone 1 and zone 2 names

    Returns
    -------
    pd.DataFrame
        3 column zone correspondence DataFrame with zone_1_to_zone_2 values
        which sum to 1 for each zone 1 id.
    """
    print('Rounding Zone Correspondences, spatial gaps in the overlap of zone 2 onto zone 1 will be equally distributed between each of zone 2 zones\n')

    # find number of zone 2 zones that each zone 1 zone divides into
    counts = zone_corr_no_slithers.groupby(f"{zone_names[0]}_zone_id").size()

    # create rounded zone correspondence
    zone_corr_rounded = zone_corr_no_slithers.loc[:,
        [
            f"{zone_names[0]}_zone_id",
            f"{zone_names[1]}_zone_id",
            f"{zone_names[0]}_to_{zone_names[1]}",
        ]
    ]

    # for zone 1 zones that only map to one zone 2 zone, set adjustment factor to 1
    zone_corr_rounded.loc[
        zone_corr_rounded[f"{zone_names[0]}_zone_id"].isin(
            counts[counts == 1].index
        ),
        f"{zone_names[0]}_to_{zone_names[1]}",
    ] = 1.0

    # calculate missing zone 1 to zone 2 adjustments for those that don't have a one to one mapping
    rest_to_round = zone_corr_rounded.loc[
        zone_corr_rounded[f"{zone_names[0]}_zone_id"].isin(
            counts[counts > 1].index
        )
    ]
    differences = (
        1
        - rest_to_round.loc
            [:,[f"{zone_names[0]}_zone_id", f"{zone_names[0]}_to_{zone_names[1]}"]]
        .groupby(f"{zone_names[0]}_zone_id")
        .sum()
    )

    # add counts to differences
    differences.loc[:, "counts"] = counts.loc[counts > 1].astype(int)

    # calculate portion of adjustment factor to add to each noham zone
    differences.loc[:, "correction"] = (
        differences.loc[:, f"{zone_names[0]}_to_{zone_names[1]}"]
        / differences.loc[:, "counts"]
    )

    # add correction to adjustment factor
    rest_to_round = rest_to_round.merge(
        differences["correction"],
        how="left",
        left_on=f"{zone_names[0]}_zone_id",
        right_on=differences.index,
    ).set_index(rest_to_round.index)

    rest_to_round.loc[:, f"{zone_names[0]}_to_{zone_names[1]}"] = (
        rest_to_round.loc[:, f"{zone_names[0]}_to_{zone_names[1]}"]
        + rest_to_round.loc[:, "correction"]
    )

    rest_to_round = rest_to_round.drop(labels="correction", axis=1)

    zone_corr_rounded[
        zone_corr_rounded[f"{zone_names[0]}_zone_id"].isin(
            rest_to_round[f"{zone_names[0]}_zone_id"]
        )
    ] = rest_to_round
    
    
    # Save rounding to final variable to turn to csv
    zone_corr_rounded_both_ways = zone_corr_rounded
    del zone_corr_rounded
    del counts
    
    # find number of zone 1 zones that each zone 2 zone divides into
        
    counts = zone_corr_no_slithers.groupby(f"{zone_names[1]}_zone_id").size()
    zone_corr_no_slithers_reindexed = zone_corr_no_slithers.reindex(columns=[f"{zone_names[0]}_zone_id",f"{zone_names[1]}_zone_id",f"{zone_names[0]}_to_{zone_names[1]}",f"{zone_names[1]}_to_{zone_names[0]}"])
    zone_corr_rounded = zone_corr_no_slithers_reindexed.loc[:,[
            f"{zone_names[1]}_zone_id",
            f"{zone_names[0]}_zone_id",
            f"{zone_names[1]}_to_{zone_names[0]}",
        ]
    ]
    

    # for zone 2 zones that only map to one zone 1 zone, set adjustment factor to 1
    zone_corr_rounded.loc[
        zone_corr_rounded[f"{zone_names[1]}_zone_id"].isin(
            counts[counts == 1].index
        ),
        f"{zone_names[1]}_to_{zone_names[0]}",
    ] = 1.0

    # calculate missing zone 2 to zone 1 adjustments for those that don't have a one to one mapping
    rest_to_round = zone_corr_rounded.loc[
        zone_corr_rounded[f"{zone_names[1]}_zone_id"].isin(
            counts[counts > 1].index
        )
    ]

    differences = (
        1
        - rest_to_round.loc
            [:,[f"{zone_names[1]}_zone_id", f"{zone_names[1]}_to_{zone_names[0]}"]]
        .groupby(f"{zone_names[1]}_zone_id")
        .sum()
    )

    # add counts to differences
    differences.loc[:, "counts"] = counts.loc[counts > 1].astype(int)

    # calculate portion of adjustment factor to add to each noham zone
    differences.loc[:, "correction"] = (
        differences.loc[:, f"{zone_names[1]}_to_{zone_names[0]}"]
        / differences.loc[:, "counts"]
    )

    # add correction to adjustment factor
    rest_to_round = rest_to_round.merge(
        differences["correction"],
        how="left",
        left_on=f"{zone_names[1]}_zone_id",
        right_on=differences.index,
    ).set_index(rest_to_round.index)

    rest_to_round.loc[:, f"{zone_names[1]}_to_{zone_names[0]}"] = (
        rest_to_round.loc[:, f"{zone_names[1]}_to_{zone_names[0]}"]
        + rest_to_round.loc[:, "correction"]
    )

    rest_to_round = rest_to_round.drop(labels="correction", axis=1)

    zone_corr_rounded[
        zone_corr_rounded[f"{zone_names[1]}_zone_id"].isin(
            rest_to_round[f"{zone_names[1]}_zone_id"]
        )
    ] = rest_to_round
    
    # Merge this result onto zone 1 to zone 2 rounding
    
    zone_corr_rounded_both_ways = zone_corr_rounded_both_ways.merge(
        zone_corr_rounded[f"{zone_names[1]}_to_{zone_names[0]}"],
        how="left",
        left_on = zone_corr_rounded_both_ways.index,
        right_on = zone_corr_rounded.index
    )
    
    zone_corr_rounded_both_ways = zone_corr_rounded_both_ways.drop(labels="key_0", axis=1)

    return zone_corr_rounded_both_ways


def missing_zones_check(zone_list, zone_names, zone_correspondence):
    """Checks for zone 1 and zone 2 zones missing from zone correspondence.

    Parameters
    ----------
    zone_list : List[gpd.GeoDataFrame, gpd.GeoDataFrame]
        Zone 1 and zone 2 GeoDataFrames.
    zone_names : List[str, str]
        Zone 1 and zone 2 names.
    zone_correspondence : pd.DataFrame
        Zone correspondence between zone systems 1 and 2.

    Returns
    -------
    pd.DataFrame
        Zone 1 missing zones.
    pd.DataFrame
        Zone 2 missing zones.
    """
    print("Checking for missing zones\n")
    
    missing_zone_1 = zone_list[0].loc[
        ~zone_list[0][f"{zone_names[0]}_zone_id"].isin(
            zone_correspondence[f"{zone_names[0]}_zone_id"]
        ),
        f"{zone_names[0]}_zone_id",
    ]
    missing_zone_2 = zone_list[1].loc[
        ~zone_list[1][f"{zone_names[1]}_zone_id"].isin(
            zone_correspondence[f"{zone_names[1]}_zone_id"]
        ),
        f"{zone_names[1]}_zone_id",
    ]
    missing_zone_1_zones = pd.DataFrame(
        data=missing_zone_1, columns=[f"{zone_names[0]}_zone_id"]
    )
    missing_zone_2_zones = pd.DataFrame(
        data=missing_zone_2, columns=[f"{zone_names[1]}_zone_id"]
    )
       
    return missing_zone_1_zones, missing_zone_2_zones

def main_zone_correspondence(
    zone_1_path,
    zone_2_path,
    zone_1_name,
    zone_2_name,
    tolerance,
    out_path,
    point_handling,
    point_tolerance,
    point_zones_path,
    lsoa_shapefile_path,
    lsoa_data_path,
    rounding,
    filter_slithers
):
    """Performs zone correspondence between two zoning systems, zone 1 and
    zone 2. Default correspondence is spatial (by zone area), but includes
    options for handling point zones with different data (for example LSOA
    employment data). Also includes option to check adjustment factors from
    zone 1 to zone 2 add to 1.

    Parameters
    ----------
    zone_1_path : str
        Path to first zone shapefile
    zone_2_path : str
        Path to second zone shapefile
    zone_1_name : str, optional
        First zone name, by default "gbfm"
    zone_2_name : str, optional
        Second zone name, by default "noham"
    tolerance : float, optional
        Tolerance for filtering out small zone overlaps, by default 0.98
    out_path : str, optional
        Path to folder to save output files, by default ""
    point_handling : bool, optional
        Whether to perform specialised point zone handling, by default False
    point_tolerance : float, optional
        Tolerance to find point zones by, where a point zone is defined as
        having zone_1_to_zone_2 < 1 - point_tolerance & zone_2_to_zone_1 >
        point_tolerance, by default 0.95
    lsoa_shapefile_path : str, optional
        Path to LSOA (or other chosen zone system for other data) shapefile,
        only necessary if point_handling True, by default ""
    lsoa_data_path : str, optional
        Path to LSOA or other chosen data, only necessary if point_handling
        True, by default ""
    rounding : bool, optional
        Whether to perform rounding, which is the check that adjustment
        factors from zone 1 to zone 2 add to 1, by default True

    Returns
    -------
    log_file: str
        Path to log file with parameters and missing zones sheet.
    len(missing_zones_1): int
        Number of zones from first zoning system missing from the final zone
        correspondence.
    len(missing_zones_2): int
        Number of zones from the second zoning system missing from the final
        zone correspondence.
    """
    

    # create log
    log_data = {
        "Run Time" : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "Zone 1 name": zone_1_name,
        "Zone 2 name": zone_2_name,
        "Zone 1 shapefile": zone_1_path,
        "Zone 2 Shapefile": zone_2_path,
        "Output directory": out_path,
        "Tolerance": tolerance,
        "Point handling": point_handling,
        "Point list": point_zones_path,
        "Point tolerance": point_tolerance,
        "LSOA data": lsoa_data_path,
        "LSOA shapefile": lsoa_shapefile_path,
        "Rounding": rounding,
        "filter_slithers" : filter_slithers,
        "type" : "correspondence",
        "method" : ""
    }

    log_df = pd.DataFrame({"Parameters": log_data.keys(), "Values": log_data.values()})

    # Update master log spreadsheet with run parameters
    # convert dict values to list
    
    list_of_elem = list(log_data.values())
    try:
        with open(os.path.join(out_path, '_master_zone_translation_log.csv'), 'a+', newline='') as write_obj:
            csv_writer = csv.writer(write_obj)
            csv_writer.writerow(list_of_elem)
    except Exception as error:
        print("Failed to add to Master Log" + str(error))

    # read in zone shapefiles
    zone_list, zone_names, zones_switch = read_zone_shapefiles(
    zone_1_path, zone_2_path, zone_1_name, zone_2_name
    )

    # produce spatial zone correspondence
    
    spatial_correspondence = spatial_zone_correspondence(zone_list, zone_names)
    
    # Convert out_path tuple to string
    out_path = ''.join(out_path)


    # Determine if slither filtering and rounding required. 
    if filter_slithers:
        print("Filtering out small overlaps.\n")
        (
            spatial_correspondence_slithers,
            spatial_correspondence_no_slithers,
        ) = find_slithers(spatial_correspondence, zone_names, tolerance)        
    
        if rounding:
            print("Checking all adjustment factors add to 1\n")
            final_zone_corr = round_zone_correspondence(spatial_correspondence_no_slithers, zone_names)
        else:
            final_zone_corr = spatial_correspondence_no_slithers
    else:
        if rounding:
            print("Checking all adjustment factors add to 1\n")
            final_zone_corr = round_zone_correspondence(spatial_correspondence, zone_names)
        else:
            final_zone_corr = spatial_correspondence
        
    # Save correspondence output
    out_path = ''.join(out_path)
    final_zone_corr_path = f"{out_path}/{zone_names[0]}_to_{zone_names[1]}_correspondence.csv"
    final_zone_corr.to_csv(
        f"{out_path}/{zone_names[0]}_to_{zone_names[1]}_correspondence.csv",
        index=False,
    )
    missing_zones_1, missing_zones_2 = missing_zones_check(
        zone_list, zone_names, final_zone_corr
        )   
    
    print(f"Missing Zones from 1 : {len(missing_zones_1)}")
    print(f"Missing Zones from 2 : {len(missing_zones_2)}\n")

    
    # Create log of missing zones

    log_file = f"{out_path}/{zone_names[0]}_to_{zone_names[1]}_missing_zones_log.xlsx"
    with pd.ExcelWriter(log_file, engine="openpyxl") as writer:
        log_df.to_excel(writer, sheet_name="Parameters", index=False)
        missing_zones_1.to_excel(writer, sheet_name=f"{zone_names[0]}_missing", index=False)
        missing_zones_2.to_excel(writer, sheet_name=f"{zone_names[1]}_missing", index=False)
        #if point_handling:
            #point_zones_info.to_excel(writer, sheet_name="point_handling", index=False)
    print(f"List of missing zones can be found in log file found here: {log_file}\n")
    print(f"Zone correspondence finished, file saved here: {final_zone_corr_path}\n")
    
    return final_zone_corr,final_zone_corr_path, zones_switch



