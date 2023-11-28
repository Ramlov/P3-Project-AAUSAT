import socket
import time
import pymysql
import threading

# Define constants 
BUFFER_SIZE = 1024
PORT = 12345
FORMAT = 'utf-8'
SERVER = "192.168.1.100" # SERVER IP address
AAU_ADDR = (SERVER, PORT)

# database = pymysql.connect(
#     host = "system-database.cwctijm9dz2w.eu-central-1.rds.amazonaws.com",
#     user = "admin",
#     password = "SunsetBeer",
#     database = "gs_system_database",
# )

# def get_data_from_database(db):
#     """
#     Getting data from GS_Table from the backend database
#     """
#     table_name = "GS_Table"
#     db_cur = db.cursor()
#     db_cur.execute(f"SELECT * FROM {table_name};")
#     gs_data = db_cur.fetchall()

#     # Example of fecting data from database ->
#     # gs_data = [["1", "AAU", "(57.0, 9.2)", "1234", "AZ 90", "IP"],
#     # ["2", "TUW", "(45.0, 9.2)", "4321", "EL 90", "IP"]]
#     print(gs_data)
#     # Slicing 
#     #     gs_id = gs_data[0][0]
#     #     gs_name = gs_data[1][1]
#     #     gs_coor = gs_data[1][2] 
#     #     sat_id = gs_data[1][6]
#     #     gs_task = gs_data[1][7]
#     #     gs_ip = gs_data[1][8]
    
#     # return gs_task


def connect_to_groundstation(gs_address, port):
    try:
        # Creating socket 
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # ipv4 address & TCP socket
        # Connecting to Ground station (Rasberry Pi)
        sock.connect((gs_address, port))
        
        # Send commands/task to Ground station
        send_thread = threading.Thread(target=send_commands, args=(sock,))
        send_thread.start()
        receive_response(sock)

        # receive commands/task from Ground station
        # receive_thread = threading.Thread(target=receive_response, args=(sock,))
        # receive_thread.start()
        # # Waiting for repsonse from Ground station
        # response = sock.recv(BUFFER_SIZE).decode()
        # print(f"Response from Ground: {gs_address} | Port: {port} -> \n {response}")

    except ConnectionRefusedError:
        print(f"Connection to Ground station address: {gs_address} | Port: {port} -> refused")

    return sock

def receive_response(sock):
    # print("hello\n")
    while True:
        response = sock.recv(BUFFER_SIZE).decode()
        if not response:
            break
        # Waiting for response from Ground station
        # print(f"Response from Ground: {gs_address} | Port: {port} -> \n {response}")
        print(f"\nReceived: {response}")

def send_commands(sock):
    while True:
        command = input("Enter command to send to server: ")
        if len(str.encode(command)) > 0:

            list_of_commands = ["y", "n", "MANUAL", "AT", "ML", "MR", "MU", "MD", "AZ", "EL", "SA", "SE"]

            if command == "quit":
                print("Disconnected")
                break      
            
            if command == 'help':
                print("""
                    Available commands:
                    MANUAL - Enter manual mode
                    AT  - AutoTrack (AAU GS only)  [int - satID]
                    AZ  - Azimuth  [number - 1 decimal place (XXX.X)]
                    EL  - Elevation  [number - 1 decimal place (YYY.Y)]
                    UP  - Uplink frequency  [in Hertz]
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
                    """)
                continue
                
            if command in list_of_commands:
                sock.send(command.encode(FORMAT))
                
                # if list_of_commands[1]:
                #     sock.send(command.encode(FORMAT))
                # elif list_of_commands[0]:
                #     sock.send(command.encode(FORMAT))
                # else:
                #     continue

                # user_input = input("Enter command to send to server: ")
                # if user_input in list_of_commands and user_input != list_of_commands[:2]:
                #     try:
                #         command, argument = user_input.split()
                #     except ValueError:
                #         print("This command does not work!")
                #         continue

                #     if command == command.lower() or command[:1].lower() or command[1:2].lower():
                #         command = command.upper()
                
                #     elif command == "AZ" and len(argument): 
                #         try:
                #             degrees = float(argument)
                #             degrees = round(degrees, 1)
                #             if 0 <= degrees <= 360:
                #                 command = f"{command} {degrees}"
                #                 sock.send(command.encode(FORMAT))
                #                 print(f"Moving azimuth {degrees} degrees")
                #             else: 
                #                 print("Invalid degrees value. Must be between 0 to 360 degrees")
                #         except ValueError:
                #             print("Invalid degrees")
                
                #     elif command == "EL" and len(argument):
                #         try: 
                #             degrees = float(argument)
                #             degrees = round(degrees, 1)
                #             if 0 <= degrees <= 180: 
                #                 command = f"{command} {degrees}"
                #                 sock.send(command.encode(FORMAT))
                #                 print(f"Moving Elevation {degrees} degrees")
                #             else:
                #                 print("Invalid degrees value. Must be between 0 to 180 degrees")
                #         except ValueError:
                #             print("Invalid degrees")
                # else:
                #     print("This command does not work! All commands except MAUNAL and AT can be used here")
                # else:
                #     print("MANUAL command needs to be sent first")
            else:
                print("This command does not work! MANUAL command needs to be sent first")
                continue
        else:
            continue

    sock.close()

if __name__ == "__main__":
    sock = connect_to_groundstation(SERVER, PORT)
    send_commands(sock)


    # # List of ground stations in the system
    # Ground_stations = [
    #     (SERVER, 9999),
    #     (SERVER, 9998)
    # ]
    
    # threads = []
    # for server in Ground_stations:
    #     address, port = server
    #     thread = threading.Thread(target=connect_to_groundstation, args=(address, port))
    #     threads.append(thread)
    #     thread.start()
    
    # for thread in threads:
    #     thread.join()