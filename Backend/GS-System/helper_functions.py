# Import Libraries
import pymysql
import time
from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timedelta
import requests
import threading


def watch_manual(database: pymysql.Connection, best_match):
    print(f"Started Watchdog for {best_match[0]}")
    
    time.sleep(20) # Await 60 seconds until the task has been "Started"

    # Declare Variables
    log = 0
    valid_log = None
    GS_ID = best_match[0]
    keywords_to_ignore = ['PP_OK', 'azimuth', 'elevation', 'PP_WAIT']
    watchdog_time = 20 # The allowing the User to do stuff without being kicked in seconds

    task_id = execute_query(database=database, sql=f"SELECT Entry FROM GS_Table WHERE GS_ID = {GS_ID}")

    while True:
        # Check if the task exists
        task_exists = execute_query(database=database, sql=f"SELECT Entry FROM GS_Table WHERE GS_ID = {GS_ID}")

        print(f"check entry from gs_table: {task_exists} for GS {GS_ID}")
        
        if task_exists == task_id:
            # Get the last Log and check if a new one exists since this one, if no, then close connection
            new_logs = execute_query(database=database, sql=f"SELECT Log_ID, Dump FROM Dump_Table WHERE GS_ID = {GS_ID} AND Log_ID > {log} ORDER BY Log_ID DESC")

            print(f"new logs: {new_logs}")
            for new_log in new_logs:
                ignorekey_found = False  # Initialize the flag for each entry
                for ignorekey in keywords_to_ignore:
                    if ignorekey in new_log[1]:
                        ignorekey_found = True
                        break

                if not ignorekey_found:
                    print(f"Valid Entry Detected: {new_log}")
                    valid_log = new_log[0]
                    break


            print(f"last valid entry: {valid_log}. entry: {log}")
            if valid_log and valid_log != log:
                log = valid_log
            else:
                # Remove The task from GS_Table
                print("Removing Task from Groundstation")
                execute_query(database=database, sql=f"UPDATE GS_Table SET Entry = NULL, Sat_ID = NULL, Method = NULL, Pass_Start = NULL, Pass_End = NULL WHERE GS_ID = {GS_ID}")
                
                break
        else:
            print("New Task assigned to GS...")
            break

        time.sleep(watchdog_time)
    
    print(f"Exiting Watchdog for {GS_ID}")


def get_TLE(sat_id):

    response = requests.get(
        url=f'https://tle.ivanstanojevic.me/api/tle/{sat_id}')

    result = response.json()

    TLE_dict = {
        'sat_name': result.get("name"),
        'line 1': result.get("line1"),
        'line 2': result.get("line2")
    }
    return TLE_dict


def gs_trajectory_match(database: pymysql.Connection, sat_id: int, gs_list: list):
    '''
    gs_list = [[GS_ID, Coords = "LAT, LON, ALT", Entry]]
    This function takes one task/entry as an input and matches it with the given list of groundstations. 
    It finds the groundstation where time until execution is shortest, but over a certain threshold.
    The best match then receives this task, and the task is removed from the queue.

    Returns
    gs_
    '''
    # Setup of satellite object
    sat_TLE = get_TLE(sat_id=sat_id)

    # ---------- Use skyfield to find passes and their timestamps ----------
    ts = load.timescale()
    # Create a Skyfield satellite object
    satellite = EarthSatellite(line1 = sat_TLE["line 1"], line2 = sat_TLE["line 2"], name = sat_TLE["sat_name"], ts = ts)

    # Declare Variables    
    MIN_LOS_TIME = 60   # seconds
    LOS_DEGS = 6        # degrees
    T_delta = 1/24      # days to look into the future

    # save best pass' start and end. Return these values when done
    best_gs = None
    pass_start = time.time() + 60*60*24*T_delta     # set first pass to the max expected time. Will be usefull when comparing pass_times
    pass_end = None                                 # 60 * 60 * 24 is 1 day in seconds

    if gs_list:
        for gs in gs_list:
            lat_lon_alt = gs[1].split(",")     # Sep "LAT., LON., ALT." into ["LAT", "LON", "ALT"]
            GS_lat = float(lat_lon_alt[0])          # make strings into floats
            GS_lon = float(lat_lon_alt[1])
            GS_alt = float(lat_lon_alt[2])

            # Make a Ground Station object
            GS = Topos(latitude_degrees=GS_lat, longitude_degrees=GS_lon, elevation_m=GS_alt)

            # Calculate the next pass - check 1 hour (1/24 days) into the future
            t = ts.now()
            times, events = satellite.find_events(GS, t, t + timedelta(days = T_delta), altitude_degrees=LOS_DEGS)

            if len(times) == 0:     # if list is empty - return None
                continue

            # loop over each pass in its entirity
            for i in range(int(len(times) / 3)):    # times is always a multiple of 3, as there are 3 events per pass: start, high, stop
                start_index = i * 3
                stop_index = start_index + 2
                start_time = times[start_index].utc_datetime().timestamp()    # unixtime of when sat enters LOS (line of sight)
                stop_time = times[stop_index].utc_datetime().timestamp()
                #print(f"groundstation: {gs}, start_time: {start_time}, stop_time: {stop_time}")

                # calc total pass duration
                pass_duration = stop_time - start_time
                if pass_duration < MIN_LOS_TIME:    # skip a pass if it is too short in duration
                    continue

                if start_time < pass_start:     # if true, found new best GS
                    best_gs = gs
                    pass_start = start_time
                    pass_end = stop_time
    
    return(best_gs, pass_start, pass_end) # Return GS_List and Time Satellite is visible to the GS


def gs_sel_algorithm(database: pymysql.Connection):
    # Variable Creation
    gs_list = []

    # Get GS_Table Data
    results_gs = execute_query(database=database, sql="SELECT GS_ID, Coords, Entry FROM GS_Table WHERE Entry IS NULL ORDER BY GS_ID ASC;")
    results_queue = execute_query(database=database, sql="SELECT Entry, Method, Sat_ID FROM Queue_Table ORDER BY Pos ASC;")

    # Change Groundstation Tuple to List
    for gs in results_gs:
        gs_list.append(gs)

    # If any GS exists on the database/network
    if results_gs:
        
        # For every task in the queue, match it with the available Groundstations
        for entry in results_queue:
            best_match = None

            if len(gs_list) > 0 and entry[1] != 3:
                # Match the entry with every available GS
                best_match, pass_start, pass_stop = gs_trajectory_match(database=database, sat_id=entry[2], gs_list=gs_list)

            elif len(gs_list) > 0:
                # Check if the GS is available for Manual Control
                for GS in gs_list:
                    if GS[0] == entry[2]:
                        best_match = GS

                        # Start Thread that Watches the Manual Task in case user closes connection
                        threading.Thread(target=watch_manual, args=(database, best_match)).start()

                        break
                
                # Add Start time to manual control of groundstation
                pass_start, pass_stop = time.time(), time.time()
                
            else:
                # Last option, no new entries of newly available GSs, therefore no reason to check.
                print("No Available Groundstations -----> Exiting GS Sel Algo")
                break

            if best_match:
                # Remove the gs from gs_list:
                print(f"Best Match: {best_match} to Entry {entry[0]}")
                gs_list.remove(best_match)

                # Move Entry to the correct GS and copy info to Log
                execute_query(database=database, 
                                sql=f"UPDATE GS_Table SET Entry = (SELECT Entry FROM Queue_Table WHERE Entry = {entry[0]}), Sat_ID = (SELECT Sat_ID FROM Queue_Table WHERE Entry = {entry[0]}), Method = (SELECT Method FROM Queue_Table WHERE Entry = {entry[0]}), Pass_Start = {pass_start}, Pass_End = {pass_stop} WHERE GS_ID = {best_match[0]};") #Best_match[0] is GS_ID
                execute_query(database=database, sql=f"INSERT INTO Log_Table (User, Sat_ID, GS_ID, Pass_Start, Pass_End) SELECT User, Sat_ID, {best_match[0]}, {pass_start}, {pass_stop} FROM Queue_Table WHERE Entry={entry[0]};")

                # Clear Entry from Queue
                execute_query(database=database, sql=f"DELETE FROM Queue_Table WHERE Entry={entry[0]}")


def old_gs_sel_algorithm(database: pymysql.Connection, new_entries: list, gs_list: list):
    # Declare Temp variables
    gs_new: list = [] # Holds the newly available groundstations

    # Get GS_Table Data
    results_gs = execute_query(database=database, sql="SELECT GS_ID, Coords, Entry FROM GS_Table ORDER BY GS_ID ASC;")
    results_queue = execute_query(database=database, sql="SELECT Entry, Method, Sat_ID FROM Queue_Table ORDER BY Pos ASC;")


    if results_gs: # If any gs exist on the database

        # Check if there are newly available GS's
        for GS in results_gs:
            if GS[2] is None and GS not in gs_list: # If the GS has no task and not previously checked, append to gs_new
                    gs_new.append(GS)

        # If an available GS exists
        if len(gs_list) > 0 or len(gs_new) > 0:
            
            if len(new_entries) > 0 and len(gs_new) == 0:
                # Only check new entries with available Groundstations
                for entry in new_entries:
                    #print(f"Checking entry: {entry}")
                    # Create Variable
                    best_match = None
                    if len(gs_list) > 0 and entry[1] != 3: # The length of the list can become 0 if a GS becomes occupied by previous entry. The second part checks the method attached (not manual)
                        best_match, pass_start, pass_stop = gs_trajectory_match(database=database, entry=entry[0], gs_list=gs_list)
                        #print(f"Best Match: {best_match}")
                        #print(f"GS List: {gs_list}")
                    
                    elif len(gs_list) > 0:
                        #print(f"Manual Connection Requested entry = {entry}")
                        # Allocate The manual task to the correct GS if Available. First get the GS_ID
                        GS_ID = execute_query(database=database, sql=f"SELECT Sat_ID FROM Queue_Table WHERE Entry = {entry[0]};")[0][0]

                        # If the Groundstation is still in the GS list, then we reserve it
                        for GS in gs_list:
                            if GS_ID == GS[0]:
                                best_match = GS

                                # Start Thread that Watches the Manual Task in case user closes connection
                                threading.Thread(target=watch_manual, args=(database, best_match)).start()

                                break

                        pass_start = time.time()
                        pass_stop = pass_start
                    
                    else:
                        break

                    if best_match:
                        # Remove the gs from gs_list:
                        gs_list.remove(best_match)

                        # Move Entry to the correct GS and copy info to Log
                        execute_query(database=database, 
                                      sql=f"UPDATE GS_Table SET Entry = (SELECT Entry FROM Queue_Table WHERE Entry = {entry}), Sat_ID = (SELECT Sat_ID FROM Queue_Table WHERE Entry = {entry}), Method = (SELECT Method FROM Queue_Table WHERE Entry = {entry}), Pass_Start = {pass_start} WHERE GS_ID = {best_match[0]};") #Best_match[0] is GS_ID
                        execute_query(database=database, sql=f"INSERT INTO Log_Table (User, Sat_ID, GS_ID, Pass_Start) SELECT User, Sat_ID, {best_match[0]}, {pass_start} FROM Queue_Table WHERE Entry={entry};")

                        # Clear Entry from Queue
                        execute_query(database=database, sql=f"DELETE FROM Queue_Table WHERE Entry={entry}")


            elif len(gs_new) > 0:
                # Add the new Gs to old gs
                gs_list.extend(gs_new)

                # Check queue with newly available Groundstations
                for entry in results_queue:
                    #print(f"Checking entry: {entry}")
                    # Best Match variable reset
                    best_match = None

                    if len(gs_list) > 0 and entry[1] != 3:
                        best_match, pass_start, pass_stop = gs_trajectory_match(database=database, entry=entry[0], gs_list=gs_list)
                        #print(f"Best Match: {best_match}")
                        #print(f"GS List: {gs_list}")
                    
                    elif len(gs_list) > 0:
                        #print(f"Manual Connection Requested entry = {entry}")
                        # Allocate The manual task to the correct GS if Available. First get the GS_ID
                        GS_ID = execute_query(database=database, sql=f"SELECT Sat_ID FROM Queue_Table WHERE Entry = {entry[0]};")[0][0]

                        # If the Groundstation is still in the GS list, then we reserve it
                        for GS in gs_list:
                            if GS_ID == GS[0]:
                                best_match = GS
                                break

                        pass_start = time.time()

                    else:
                        break

                    if best_match:
                        gs_list.remove(best_match)

                        # Move Entry to the correct GS and copy info to Log
                        execute_query(database=database, 
                                      sql=f"UPDATE GS_Table SET Entry = (SELECT Entry FROM Queue_Table WHERE Entry = {entry[0]}), Sat_ID = (SELECT Sat_ID FROM Queue_Table WHERE Entry = {entry[0]}), Method = (SELECT Method FROM Queue_Table WHERE Entry = {entry[0]}), Pass_Start = {pass_start} WHERE GS_ID = {best_match[0]};") #Best_match[0] is GS_ID
                        execute_query(database=database, sql=f"INSERT INTO Log_Table (User, Sat_ID, GS_ID, Pass_Start) SELECT User, Sat_ID, {best_match[0]}, {pass_start} FROM Queue_Table WHERE Entry={entry[0]};")
                        
                        # Clear Entry from Queue
                        execute_query(database=database, sql=f"DELETE FROM Queue_Table WHERE Entry={entry[0]}")
            else:
                # Last option, no new entries of newly available GSs, therefore no reason to check.
                print("No available Entry ---> GS matching options")

    return gs_list


def queue_controller(database: pymysql.Connection):

    # Declare Variables
    sort_queue = False

    # Fetch Necessary Columns From Queue Table
    results = execute_query(database=database, sql="SELECT Entry, Prio, Pos, Method FROM Queue_Table ORDER BY Prio ASC, Entry ASC;")

    if results: # No reason to sort or work on empty queue

        # Check for new entry in the queue table and sort the queue based on Entry and Priority
        i = 0
        for z in range(2): # Check the queue twice: 1. Check if we have new entry(ies), 2. Sort the order if that is the case.
            if z == 1 and sort_queue == False: # If there are no new entries then no reason to reorder
                break

            for task in results:
                if sort_queue == False and task[2] is None: # If a new entry is registered then start rearranging.
                    sort_queue = True
                    break # Go to next stage where we sort the queue (Breaks out of first for loop)

                if sort_queue == True: # Reorder Queue 
                    i += 1
                    execute_query(database=database, sql=f"UPDATE Queue_Table SET Pos = {i} WHERE Entry = {task[0]} AND Prio = {task[1]};") # update position in queue

        return(True) # Return possible new entries, and that the queue isn't empty
    
    else:
        return(False) # Return the queue is empty


def drop_tables(database: pymysql.Connection):
    execute_query(database=database, sql="DROP TABLE IF EXISTS Queue_Table, GS_Table, Log_Table, Dump_Table;")


def db_setup(database: pymysql.Connection):
    try:
        # Create Queue Table
        execute_query(database=database, sql="CREATE TABLE Queue_Table (Entry INT AUTO_INCREMENT PRIMARY KEY, Sat_ID INT, User VARCHAR(255), Method INT, Prio INT, Pos INT);")

        # Create GS-Table
        execute_query(database=database, sql="CREATE TABLE GS_Table (GS_ID INT PRIMARY KEY, GS_Name VARCHAR(255), Coords VARCHAR(255), IP VARCHAR(45), Entry INT, Sat_ID INT, Method INT, Pass_Start FLOAT, Pass_End FLOAT);") # Coords are 'long, lat, alt'

        # Create Log_Table
        execute_query(database=database, sql="CREATE TABLE Log_Table (Log_ID INT AUTO_INCREMENT PRIMARY KEY, Sat_ID INT, User VARCHAR(255), Method INT, GS_ID INT, Pass_Start FLOAT, Pass_End FLOAT);")

        # Create Log_Table
        execute_query(database=database, sql="CREATE TABLE Dump_Table (Log_ID INT AUTO_INCREMENT PRIMARY KEY, GS_ID INT, Dump VARCHAR(1000));")

        execute_query(database=database, sql="INSERT INTO GS_Table (GS_ID, GS_Name, Coords, IP, Entry, Sat_ID, Method, Pass_Start, Pass_End) VALUES (1, 'AAU GS', '57.0139449, 9.9875578, 21.0', NULL, NULL, NULL, NULL, NULL, NULL);")
        return ("Tables Created")

    except Exception as e:
        print(f"Issue Creating Tables in Database: {e}")
        return (e)


def execute_query(database: pymysql.Connection, sql):
    with database.cursor() as cursor:
        results = 0
        cursor.execute(sql)
        results = cursor.fetchall()
        database.commit()
    return(results)