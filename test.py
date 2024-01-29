import serial
import threading
import argparse
import json
import requests
from datetime import datetime, timezone, timedelta
import socket
import pymysql
from time import sleep
import RPi.GPIO as GPIO
from update_time import update_time_ntp

GPIO.setmode(GPIO.BCM)
control_pin = 23

GPIO.setup(control_pin, GPIO.OUT)

host = '172.26.12.59'
port = 13446
version = "Raspberry pi version: 1.1.7"

firstresponders = "write START when ready to connect to ESP32: "

# Define the serial port and baud rate
serial_port = '/dev/ttyUSB0'

baud_rate = 115200


db_info = {
    "host": "system-database.cwctijm9dz2w.eu-central-1.rds.amazonaws.com",
    "port": 3306,
    "user": "admin",
    "password": "SunsetBeer",
    "database": "gs_system_database"
}

db_connection = pymysql.connect(**db_info)
db_cursor = db_connection.cursor()



while True:
    try:
        # Initialize the serial connection
        serial_port = '/dev/ttyUSB0'
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port} successfully!")
        break  # exit the loop if the connection is successful
    except serial.SerialException:
        print(f"Failed to connect to {serial_port}. Retrying in 5 seconds...")
        sleep(3)
    try:
        # Initialize the serial connection
        serial_port = '/dev/ttyUSB1'
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        print(f"Connected to {serial_port} successfully!")
        break  # exit the loop if the connection is successful
    except serial.SerialException:
        print(f"Failed to connect to {serial_port}. Retrying in 5 seconds...")
        sleep(3)

connected_clients = []
send_thread_running = False

def read_and_print_output(client_socket):
    gs_id = 1
    global send_thread_running
    raw = False
    if client_socket == "MAN":
        while True:
            response = ser.readline().decode('utf-8', errors='replace').strip()
            #print(response)
            if response:
                try:
                    insert_query = "INSERT INTO Dump_Table (Dump, GS_ID) VALUES (%s, %s)"
                    #print(gs_id)
                    db_cursor.execute(insert_query, (response, gs_id,))
                    db_connection.commit()
                except:
                    pass
                if raw:
                    print(response)
                    #client_socket.send(response.encode())
                else:
                    try:
                        print(response)
                        process_response(response)
                        #client_socket.send(process_response(response).encode())
                    except:
                        pass
    else:
        while True:
            if send_thread_running == False:
                break
            try:
                response = ser.readline().decode().strip()
            except:
                print("Error respond")
                response = ""
            if response:
                try:
                    insert_query = "INSERT INTO Dump_Table (Dump, GS_ID) VALUES (%s, %s)"
                    #print(gs_id)
                    db_cursor.execute(insert_query, (response, gs_id,))
                    db_connection.commit()
                except:
                    pass
                #print(connected_clients)
                #print(client_socket)
                print(response)
                if raw:
                    client_socket.send(response.encode())
                else:
                    try:
                        process_response(response)
                        client_socket.send(response.encode())
                        #client_socket.send(process_response(response).encode())
                    except:
                        pass

def process_response(response):
    parts = response.split("_")
    try:
        command, status = parts[0], parts[1]
        if status == "OK":
            return(f"{command} OK")
        elif status == "WAIT":
            return(f"{command} is in progress. Waiting for completion...")
        elif status == "TLE":
            status = update_time_ntp()
            tle = get_TLE(parts[2])
            json_str = json.dumps(tle)
            encoded_data = (json_str + '\n').encode()
            ser.write(encoded_data)
            #print("test")
            return(tle)
        elif status == "TIME":
            current_time = datetime.now(timezone.utc)
            denmark_timezone = timezone(timedelta(hours=1))
            current_time_denmark = current_time.astimezone(denmark_timezone)
            epoch_time = str(int(current_time_denmark.timestamp()))
            #print(epoch_time)
            ser.write(epoch_time.encode() + b'\n')
            #return("TIME UPDATE")
        elif command == "VE":
            return(f"{command} {parts[1]}")
        elif status == "ERROR":
            return(f"{command} encountered an error.  \n Enter a command (or 'help' for command list): ")
            if len(parts) >= 3:
                error_code = parts[2]
                return(f"Error Code: {error_code}  \n Enter a command (or 'help' for command list): ")
    except:
        return("RAW OUTPUT: ", response)

def send_user_commands():
    while True:
        command = input("")
        list_of_commands = ["n", "y", "MANUAL", "AT", "ML", "MR", "MU", "MD", "AZ", "EL", "SA", "SE"]
        if command == 'help':
            print("""
                Available commands:
                MANUAL - Enter manual mode
                AT  - AutoTrack (AAU GS only)  [int - satID]
                AZ  - Azimuth  [number - 1 decimal place (XXX.X)]
                EL  - Elevation  [number - 1 decimal place (YYY.Y)]
                UP  - Uplink frequency  [in Hertz] - Not implemented
                DN  - Downlink frequency  [in Hertz]
                DM  - Downlink mode  [ascii, e.g., FM]
                UM  - Uplink mode  [ascii, e.g., FM]
                ML  - Move left
                MR  - Move right
                MU  - Move up
                MD  - Move down
                SA  - Stop azimuth
                SE  - Stop elevation
                SV  - Show variables
                VE  - Request version
                START - Power on ESP32
                STOP - Power down ESP32
                """)
        elif command == "START":
            print("Received START command. Setting pin HIGH.")
            GPIO.output(control_pin, GPIO.HIGH)
        elif command == "STOP":
            print("Received STOP command. Setting pin LOW.")
            GPIO.output(control_pin, GPIO.LOW)
        elif command in list_of_commands or 1 == 1:
            if command == "VE":
                ser.write(command.encode() + b'\n')
                print(version)
            else:
                ser.write(command.encode() + b'\n')
        else:
            print("Commands do not exist!")

current_client = None  # Variable to store the current connected client

def handle_client(client_socket):
    global current_client
    global send_thread_running
    send_thread_running = False
    sleep(1)

    # Set the current client to the new client
    current_client = client_socket

    # Add the client to the list of connected clients
    connected_clients.append(client_socket)
    print(connected_clients)
    # Restart the send_thread if it's not running
    send_thread_running = True
    send_thread = threading.Thread(target=read_and_print_output, args=(client_socket,))
    send_thread.start()

    while True:
        try:
            data = current_client.recv(1024)  # Use current_client instead of client_socket
            if not data:
                print("Client disconnected.")
                GPIO.output(control_pin, GPIO.LOW)
                break  # Break out of the loop if the client disconnects
            if data.decode() == "START":
                print("STARTING")
                GPIO.output(control_pin, GPIO.HIGH)
            elif data.decode() == "STOP":
                print("sleeping for stop")
                sleep(3)
                print("STOPPGINASIDNASOIDJNAS")
                GPIO.output(control_pin, GPIO.LOW)
            else:
                print(data)
                ser.write(data + b'\n')
                if data.decode() == "VE":
                    # Send version to all connected clients
                    for client in connected_clients:
                        client.send(version.encode())
        except ConnectionResetError:
            GPIO.output(control_pin, GPIO.LOW)
            sleep(2)
            print("Client connection reset by peer.")
            send_thread_running = False
            break  # Break out of the loop if there's a connection reset
        except Exception as e:
            print(f"Error handling client: {e}")
            break  # Break out of the loop if there's an unexpected error

    # Remove the client from the list of connected clients
    try:
        connected_clients.remove(current_client)
    except ValueError:
        pass  # Ignore if the client is not in the list

    try:
        current_client.close()  # Close the client socket
    except:
        pass

    # Check if there are still connected clients
    if not connected_clients:
        send_thread_running = False

    # Reset the current client to None when the client disconnects
    current_client = None
    send_thread.join()

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







if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 Control Program")
    parser.add_argument("mode", choices=["MAN", "TUN"], help="Operating mode (MAN or TUN)")
    # parser.add_argument("raw", choices=["True", "False"], help="Raw output (True or False)")
    args = parser.parse_args()
    GPIO.output(control_pin, GPIO.LOW)
    if args.mode == "MAN":
        print("Write START when ready!")
        command_thread = threading.Thread(target=send_user_commands)
        output_thread = threading.Thread(target=read_and_print_output, args=("MAN",))
        output_thread.start()
        command_thread.start()
        output_thread.join()
        command_thread.join()

    elif args.mode == "TUN":
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"Server listening on {host}:{port}")
        while True:
            client_socket, client_address = server_socket.accept()
            print("Connection from", client_address)
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
    else:
        print("Invalid mode. Use 'MAN' or 'TUN' as the mode argument. \n MAN for Manual control through the Terminal \n TUN for using the tunnel to the backend.")
        exit(1)

ser.close()