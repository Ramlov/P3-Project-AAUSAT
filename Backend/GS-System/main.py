# Import Libraries
import os, time
import pymysql
from dotenv import load_dotenv

# Import Helper Functions
from helper_functions import db_setup, execute_query, drop_tables, queue_controller, gs_sel_algorithm

def main():
    # Declare Variables
    new_entries: list = [] # This list will hold the user submitted tasks when they are first discovered by the backend. Used in gs_sel_algo.
    gs_list: list = [] # This list will hold GS which has already been paired against the queue with no luck. Used to avoid double checking tasks against the same GS
    printed = False

    # Load Configuration File
    load_dotenv()

    HOST = os.getenv('HOST')
    PORT = os.getenv('PORT')
    DB_NAME = os.getenv('DB-NAME')
    USER = os.getenv('USER')
    PASSWORD = os.getenv('PASSWORD')

    # Connect to Database
    database = pymysql.connect(
        host = HOST,
        user = USER,
        password = PASSWORD,
        database = DB_NAME
    )

    # drop_tables(database=database)

    # Connect if the Database is empty
    if not execute_query(database=database, sql="SHOW TABLES"):
        print("The Database is empty. Creating Tables...")
        print(db_setup(database=database))
    else:
        print("Database contains data - Assumed it has been setup.")

    # Backend Error Handler - Detect Bugs for now
    print("Starting Backend Server")

    while True:
        # Run Queue Controller/Algorithm
        new_entries, queue_check = queue_controller(database=database)

        if queue_check == True: # If there are items in the queue
            print("Submission Found - Running Groundstation Selection Algorithm")
            gs_list = gs_sel_algorithm(database=database, new_entries=new_entries, gs_list=gs_list)
            printed = False
        
        else:
            if printed == False:
                print("The Queue is empty")
                print("Awaiting Submission in Queue")
                printed = True

        #Run every 5 sec
        time.sleep(3)


if __name__ == "__main__":
    main()