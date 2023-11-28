from json import load
import pymysql
import time
import backend_rpi_tunnel as brt
import socket
import threading


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
        if tracking_mode == "MANUAL":
            sat_id = data['groundstation_id']
            prio = data['priority']
            method = 3
            user= "Dinmor"
            task = data.get('task', '') # default value for task
            self.db_cur.execute(f'INSERT INTO Queue_Table (Sat_ID, User, Method, Task, Prio) VALUES (%s, %s, %s, %s, %s)', (sat_id, user, method, task, prio))
            self.database.commit()
            
            # Collecting latest entry from queue table, to be able to identify it in the GS table
            query = (f"SELECT Entry FROM Queue_Table WHERE User = %s ORDER BY Entry DESC LIMIT 1")
            self.db_cur.execute(query, (user,))
            entry = self.db_cur.fetchone()[0]
            print(entry)
            self.check_available(sat_id, entry)

        elif tracking_mode == "AUTOTRACKING":
            sat_id = data['satellite_id']
            prio = data['priority']
            method = 2 # 2 eller 3 
            user = "dinfar"
            task = "AT"
            self.db_cur.execute(f'INSERT INTO Queue_Table (Sat_ID, User, Method, Task, Prio) VALUES (%s, %s, %s, %s, %s)', (sat_id, user, method, task, prio))
            self.database.commit()

            # Collecting latest entry from queue table, to be able to identify it in the GS table
            query = (f"SELECT Entry FROM Queue_Table WHERE User = %s ORDER BY Entry DESC LIMIT 1")
            self.db_cur.execute(query, (user,))
            entry = self.db_cur.fetchone()[0]
            print(entry)
            # self.check_available(sat_id, entry)


    def check_available(self, sat_id, entry):
        while True:
            time.sleep(2)
            query = "SELECT Entry FROM GS_Table WHERE GS_ID = %s"
            self.db_cur.execute(query, (sat_id,))
            try:
                result = self.db_cur.fetchone()[0]
            except:
                result = None
            print(result)
            
            if entry == result:
                print("Open Tunnel")
                return True
            self.database.commit()

    
    def close_connection(self):
        self.db_cur.close()
        self.database.close()
    
    def open_tunnel(self):
        aau = self.config["groundstations"][0]
        gs_address = aau["gs_address"]
        port = aau["port"]
        self.connect_to_groundstation(gs_address, port)
        

    def connect_to_groundstation(self, gs_address, port):
        try:
            # Creating socket 
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # ipv4 address & TCP socket
            # Connecting to Ground station (Rasberry Pi)
            self.sock.connect((gs_address, port))

            # receive_thread = threading.Thread(target= self.receive_response(), args=())
            # receive_thread.start()

        except ConnectionRefusedError:
            print(f"Connection to Ground station address: {gs_address} | Port: {port} -> refused")

    def send_commands(self, command):
        operation = []
        responses = []

        for key, value in command.items():
            if key == "el":
                operation.append(key + value)
            elif key == "az":
                operation.append(key + value)
            else:
                operation.append(value)

        for item in operation:
            print(operation)
            print(item)
            self.sock.send(item.encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8')
            responses.append(response)
        print( responses)