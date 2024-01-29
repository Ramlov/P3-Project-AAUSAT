# Import Libraries
import os, time
import pymysql
from dotenv import load_dotenv

# Import Helper Functions
from helper_functions import db_setup, execute_query, drop_tables, queue_controller, gs_sel_algorithm
clear_db = True
def main():
    # Declare Variables
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
    if clear_db:
        drop_tables(database=database)

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
        queue_check = queue_controller(database=database)

        if queue_check == True: # If there are items in the queue
            print("Submission Found - Running Groundstation Selection Algorithm")
            gs_sel_algorithm(database=database)
            printed = False
        
        else:
            if printed == False:
                print("The Queue is empty")
                print("Awaiting Submission in Queue")
                printed = True

        #Run every 3 sec
        time.sleep(3)


if __name__ == "__main__":
    main()