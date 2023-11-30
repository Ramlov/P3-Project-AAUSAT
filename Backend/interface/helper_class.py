from json import load
import pymysql
import time
import socket
import threading
import requests
from time import sleep

class helper:
    def __init__(self):
        with open('config.json', 'r') as f:
            self.config = load(f)
        self.database = pymysql.connect(**self.config["database"])
        self.database.autocommit(True)
        self.db_cur = self.database.cursor()
        self.sock = None
        self.BUFFER_SIZE = 1024
        self.FORMAT = 'utf-8'

    def data_tunnel(self, data):
        print(data)
        tracking_mode = data["tracking_mode"]
        prio = data['priority']

        if tracking_mode == "MANUAL":
            user = "Dinmor"
            method = 3
            sat_id = data['groundstation_id']
        elif tracking_mode == "AUTOTRACKING":
            user = "Dinfar"
            method = 2
            sat_id = data['satellite_id']

        self.db_cur.execute(f'INSERT INTO Queue_Table (Sat_ID, User, Method, Prio) VALUES (%s, %s, %s, %s)', (sat_id, user, method, prio))
        self.database.commit()
        
        # Collecting latest entry from queue table, to be able to identify it in the GS table
        query = (f"SELECT Entry FROM Queue_Table WHERE User = %s ORDER BY Entry DESC LIMIT 1")
        self.db_cur.execute(query, (user,))
        entry = self.db_cur.fetchone()[0]
        print(entry)

        gs_id = self.check_available(sat_id, entry)
        print(f"GSID in datatunnel: {gs_id}")

        return gs_id


    def check_available(self, sat_id, entry):
        while True:
            time.sleep(2)
            query = "SELECT GS_ID, Entry FROM GS_Table"
            self.db_cur.execute(query)
            try:
                result = self.db_cur.fetchall()
            except:
                result = None
            print(result)
            
            for gs in result:
                if entry == gs[1]:
                    print("Open Tunnel")
                    return gs[0]
                
            self.database.commit()

    
    def close_connection(self):
        self.db_cur.close()
        self.database.close()
    
    def open_tunnel(self, gs_id):
        print("gs_id in open_tunnel: ", gs_id)
        groundstation = self.config["groundstations"][int(gs_id)-1]
        gs_address = groundstation["gs_address"]
        port = groundstation["port"]
        self.connect_to_groundstation(gs_address, port)

        

    def connect_to_groundstation(self, gs_address, port):
        try:
            # Creating socket 
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # ipv4 address & TCP socket
            self.sock.connect((gs_address, port))

            print(self.sock)

            # receive_thread = threading.Thread(target= self.receive_response(), args=())
            # receive_thread.start()

        except ConnectionRefusedError:
            print(f"Connection to Ground station address: {gs_address} | Port: {port} -> refused")

    def send_commands(self, command):
        operation = []
        responses = []

        for key, value in command.items():
            if key == "el":
                key = key.upper()
                operation.append(key + value)
            elif key == "az":
                key = key.upper()
                operation.append(key + value)
            elif value == "STOP":
                operation.append(value)
                self.remove_task_from_db()
                # sql = "UPDATE GS_Table SET Entry = NULL, Sat_ID = NULL, Method = NULL, Pass_Start = NULL, Pass_End = NULL WHERE GS_ID = 1"
                # self.db_cur.execute(sql)
                # self.database.commit()
                # try:
                #     with self.database.cursor() as cursor:
                #         sql = "DELETE FROM GS_Table WHERE GS_ID = 1"
                #         cursor.execute(sql)
                #         self.database.commit()

                # finally:
                #     self.database.close()
            else:
                operation.append(value)
        for item in operation:
            if not self.sock:
                return None
            self.sock.send(item.encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8')
            responses.append(response)
        return(responses)
        
    def send_auto_command(self, satellite_id, gs_id):
            sleep(5)
            AT_command = "AT" + str(satellite_id)
            print(AT_command)
            self.sock.send(AT_command.encode(self.FORMAT))
    
    def check_notrack(self, satellite_id, gs_id):
        # Initialize Variable
        lock_on = False
        
        while True:
                query = f"SELECT Dump FROM Dump_Table WHERE GS_ID = {gs_id} ORDER BY Log_ID DESC"
                self.db_cur.execute(query)
                response = self.db_cur.fetchone()
                self.database.commit()

                print(response)

                if response:
                    if response[0] == "OK - LOCK_ON: True": 
                        print(f"[LOCK ON]: Currently tracking {satellite_id}")
                        lock_on = True

                    elif response[0] == "SATELLITE-BELOW-HORIZON":
                        if lock_on == True:
                            print("Autotrack done")
                            self.remove_task_from_db()
                            return False

                    elif response[0] == "OK - LOCK_ON: False":
                        print(f"[LOCK OFF]: Not tracking {satellite_id}")
                        lock_on = True

                    else:
                        time.sleep(1)
                        print("Waiting for status response from Esp32")



    def remove_task_from_db(self):
        query = "UPDATE GS_Table SET Entry = NULL, Sat_ID = NULL, Method = NULL, Pass_Start = NULL, Pass_End = NULL WHERE GS_ID = 1"
        self.db_cur.execute(query)
        self.database.commit()
    
    def get_timestamps_for_satID(self, sat_id):
        query = "SELECT (Pass_Start, Pass_Stop) FROM GS_Table WHERE GS_ID = %s"
        self.db_cur.execute(query, (sat_id,))
        try:
            result_start = self.db_cur.fetchone()[0]
            result_stop = self.db_cur.fetchone()[0]
        except:
            result_start, result_stop = None
        print("Pass Start:", result_start)
        print("Pass Stop:", result_stop)
        self.database.commit()
