import socket

def scan_ports(target_host, start_port, end_port):

    print("Scanning ", {target_host}, " from ", {start_port}, "to", {end_port})

    for port in range(start_port, end_port + 1): #range starts right before end so add +1
        try:
            #creating new socket object
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #AF_INET is ipv4 and SOCK_STREAM is TCP socket
            #set timeout for connections to 1 second so program does not take forever to connect to unreachable ports
            s.settimeout(1)

            result = s.connect_ex((target_host, port)) #double brackets because AF_INET works as 1 argument
            #attempt to connect to target port, connect_ex return 0 if successfull or non-zero otherwise

            if result == 0:
                print(f"port", {port}, " is OPEN")
            else: 
                print(f"port ", {port}, " is CLOSED")
            s.close()

        except socket.gaierror: #socket.gaierror specific exception when a hostname to an ip fails
            print("Hostname not resolved")
            break
        except socket.error: # socket.error exception for network failure
            print("network failed to connect")
            break
        except Exception as e: #prints any error code
            print(f"An error has occured: {e}")
            break

if __name__ == "__main__": # function to enter the target host and port range
    target = input("Enter the target IP address or hostname: ")
    try:
        start = int(input("Enter the starting port number: "))
        end = int(input("Enter the end port number: "))
        scan_ports(target, start, end) 
    except ValueError: #checks for a value that is not working 
        print("Invalid port number. enter an integer")
            