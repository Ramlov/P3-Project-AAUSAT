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
            else:
                print("This command does not work! MANUAL command needs to be sent first")
                continue
        else:
            continue

    sock.close()

if __name__ == "__main__":
    sock = connect_to_groundstation(SERVER, PORT)
    send_commands(sock)
