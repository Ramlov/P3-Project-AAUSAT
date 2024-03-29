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
        self.entry = None

    def data_tunnel(self, data):
        print(data)
        tracking_mode = data["tracking_mode"]
        prio = data['priority']

        if tracking_mode == "MANUAL":
            user = "Manual1"
            method = 3
            sat_id = 1
        elif tracking_mode == "AUTOTRACKING":
            user = "Auto1"
            method = 2
            sat_id = data['satellite_id']
        elif tracking_mode == "AUTOINPUT":
            user = "Auto1"
            method = 2
            sat_id = data['satellite_id']

        self.db_cur.execute(f'INSERT INTO Queue_Table (Sat_ID, User, Method, Prio) VALUES (%s, %s, %s, %s)', (sat_id, user, method, prio))
        self.database.commit()
        
        query = (f"SELECT Entry FROM Queue_Table WHERE User = %s ORDER BY Entry DESC LIMIT 1")
        self.db_cur.execute(query, (user,))
        self.entry = self.db_cur.fetchone()[0]
        print(f'Position in queue: {self.entry}')
        return(self.entry, prio, tracking_mode, sat_id)


    def check_available(self, entry):
        if entry is None:
            print("Entry is None. Cannot proceed.")
            return None, None, None

        query = "SELECT GS_ID, Entry FROM GS_Table ORDER BY Entry ASC"
        self.db_cur.execute(query)
        
        try:
            result = self.db_cur.fetchall()
        except Exception as e:
            print(f"Error fetching results: {e}")
            return None, None, None

        if not result:
            print("No results found in GS_Table.")
            return None, None, None

        current_task_at_selected_gs = None
        tasks_in_front_of_you = None

        for gs in result:
            if gs[1] is not None:
                current_task_at_selected_gs = gs[1]
                break

        if current_task_at_selected_gs is not None:
            tasks_in_front_of_you = max(0, entry - current_task_at_selected_gs)
            print(f'Current task at selected GS: {current_task_at_selected_gs}')
            print(f'Task(s) in front of you: {tasks_in_front_of_you}')
        else:
            print("No valid current task found in GS_Table.")

        for gs in result:
            if gs[1] == entry:
                print("Open Tunnel")
                return gs[0], current_task_at_selected_gs, tasks_in_front_of_you

        return None, current_task_at_selected_gs, tasks_in_front_of_you


        
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
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            gs_address = "172.26.12.59"
            port = 13446
            self.sock.connect((gs_address, port))
            print(self.sock)

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

            else:
                operation.append(value)
        for item in operation:
            if not self.sock:
                return None
            self.sock.send(item.encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8')
            responses.append(response)
        return(responses)
        
    def send_auto_command(self, satellite_id):
            sleep(2)
            AT_command = "AT" + str(satellite_id)
            print(AT_command, "Debug")
            self.sock.send(AT_command.encode(self.FORMAT))
    
    def check_notrack(self, satellite_id, gs_id):
        # Initialize Variable
        lock_on = False
        
        while True:
            sleep(2)
            query = f"SELECT Dump FROM Dump_Table WHERE GS_ID = {gs_id} ORDER BY Log_ID DESC"
            self.db_cur.execute(query)
            response = self.db_cur.fetchone()
            self.database.commit()

            if response:
                if response[0] == "OK - LOCK_ON: True": 
                    print(f"[LOCK ON]: Currently tracking {satellite_id}")
                    lock_on = True

                elif response[0] == "SATELLITE-BELOW-HORIZON" and lock_on == True:
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
        query = "SELECT Pass_Start, Pass_End FROM GS_Table WHERE Sat_ID = %s"
        self.db_cur.execute(query, (sat_id,))
        try:
            result = self.db_cur.fetchone()
            result_start = result[0] if result else None
            result_stop = result[1] if result else None
        except Exception as e:
            print(f"Error fetching timestamps: {e}")
            result_start, result_stop = None, None
        print("Pass Start:", result_start)
        print("Pass Stop:", result_stop)
        print(type(result_start))

        self.database.commit()
        return result_start, result_stop

