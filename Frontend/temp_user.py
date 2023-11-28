import pymysql

HOST = "system-database.cwctijm9dz2w.eu-central-1.rds.amazonaws.com"
PORT = "3306"
DB_NAME = "gs_system_database"
USER = "admin"
PASSWORD = "SunsetBeer"

# Connect to Database
database = pymysql.connect(
    host = HOST,
    user = USER,
    password = PASSWORD,
    database = DB_NAME
)

#INSERT INTO GS_Table (GS_ID, GS_Name, Coords, IP, Entry, Sat_ID, Method, Pass_Start, Pass_End) VALUES (1, 'AAU GS', '57.0139449, 9.9875578, 21.0', NULL, NULL, NULL, NULL, NULL, NULL);
#INSERT INTO Queue_Table (Sat_ID, User, Method, Prio) VALUES (1562, 'Jensa', 1, 2)
with database.cursor() as cursor:
    while True:
        sql = input()
        if sql == "exit":
            break
        cursor.execute(sql)
        results = cursor.fetchall()
        database.commit()
        print(f"{results}\n")