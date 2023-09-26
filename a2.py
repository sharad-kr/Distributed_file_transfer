import socket
from time import perf_counter
import threading

lines = {}

MAX_LINES = 1000

OTHER_CLIENTS = 3
lines_received = []

connected_clients = 0

ENTRY_NUMBER = "2021CS10581"
TEAM_NAME = "slowbrains"

server_conn = socket.socket()

# sockets from which unique lines are sent to other clients
sending_client_sockets = []

# sockets from which unique lines are received from other clients
receiving_client_sockets = []

# threads receiving and processing the lines from other clients
receiving_threads = []

stop_event = threading.Event()


def worker_function(i):
    conn, address = receiving_client_sockets[i].accept()
    line_number = 0
    content = ""
    reading_content = False
    while not stop_event.is_set():
        data = conn.recv(4096)
        response = data.decode("utf-8")
        for j in range(len(response)):
            if response[j] == '\n':
                if reading_content:
                    global lines_received
                    lines[line_number] = content
                    lines_received[i] += 1
                    line_number = 0
                    content = ""
                reading_content = not reading_content
            elif not reading_content:
                line_number = 10 * line_number + (ord(response[j]) - ord('0'))
            else:
                content += response[j]


def receive_response():
    data = server_conn.recv(4096)
    response = data.decode("utf-8")
    if len(response) == 0:
        try:
            return receive_response()
        except:
            return ""
    else:
        return response


def connect_to_server(cmd_arg):
    if len(cmd_arg) == 0:
        print("Enter the IP Address and Port of the server")
        return
    tokens = cmd_arg.split(":")
    if len(tokens) != 2:
        print("Invalid format, type 'SERVER {IP_ADDRESS}:{HOST}'")
        return
    ip_address = tokens[0]
    port = int(tokens[1])
    try:
        server_conn.connect((ip_address, port))
        print("Connected to server", ip_address)
    except:
        print("Error connecting to", ip_address)


def connect_to_client(cmd_arg):
    if len(cmd_arg) == 0:
        print("Enter the IP Address and Port of the client")
        return
    tokens = cmd_arg.split(":")
    if len(tokens) != 2:
        print("Invalid format, type 'CLIENT {IP_ADDRESS}:{HOST}'")
        return
    ip_address = tokens[0]
    port = int(tokens[1])
    try:
        global connected_clients
        sending_client_sockets.append(socket.socket())
        sending_client_sockets[connected_clients].connect((ip_address, port))
        connected_clients += 1
        print("Connected to client", ip_address)
    except:
        print("Error connecting to client", ip_address)


def infinite_requests():
    start = perf_counter()
    successful_requests = 0
    line_number = 0
    content = ""
    reading_content = False
    completed_line = False
    def receive_line():
        nonlocal content, line_number, reading_content, successful_requests, completed_line
        data = server_conn.recv(4096)
        response = data.decode("utf-8")
        for i in range(len(response)):
            if response[i] == '\n':
                if reading_content:
                    if line_number not in lines and line_number >= 0 and line_number < MAX_LINES:
                        lines[line_number] = content
                        # sending_data.put(str(line_number) + "\n" + content + "\n")
                        for client in sending_client_sockets:
                            try:
                                client.send(str.encode(f"{line_number}\n{content}\n"))
                            except:
                                pass
                    line_number = 0
                    content = ""
                    completed_line = True
                    if line_number >= 0 and line_number < MAX_LINES:
                        successful_requests += 1
                reading_content = not reading_content
            elif not reading_content:
                line_number = 10 * line_number + (ord(response[i]) - ord('0'))
            else:
                content += response[i]
    while len(lines) < MAX_LINES:
        try:
            server_conn.send(str.encode("SENDLINE\n"))
        except:
            print("Error sending command to server, make sure the server is connected")
            return
        completed_line = False
        while not completed_line:
            receive_line()
    else:
        print(f"Completed in {perf_counter() - start} seconds with {successful_requests} successful requests from this client")
        submit_lines()
        if len(lines_received) > 0:
            print("Received lines from other clients: ", end = "")
        for i in lines_received:
            print(i, end = " ")
        print()
        for i in range(len(lines_received)):
            lines_received[i] = 0


def submit_lines():
    submit_data = f"SUBMIT\n{ENTRY_NUMBER}@{TEAM_NAME}\n"
    submit_data += str(len(lines)) + "\n"
    line_list = []
    for i in lines:
        line_list.append((i, lines[i]))
    line_list.sort()
    for i in line_list:
        submit_data += str(i[0]) + "\n" + i[1] + "\n"
    server_conn.send(str.encode(submit_data))
    response = receive_response()
    print(response, end = "")


def reset_session():
    server_conn.send(str.encode("SESSION RESET\n"))
    response = receive_response()
    print(response, end = "")


def get_incorrect_lines():
    server_conn.send(str.encode("SEND INCORRECT LINES\n"))
    response = receive_response()
    print(response, end = "")


def get_argument(cmd):
    tokens = cmd.split(' ')
    if len(tokens) < 2:
        return ""
    else:
        return tokens[1]


def set_entry_number(new_entry_number):
    global ENTRY_NUMBER
    if len(new_entry_number) == 0:
        print("Invalid entry number")
        return
    ENTRY_NUMBER = new_entry_number
    print(f"Successfully set entry number to {ENTRY_NUMBER}")


def handle_command(cmd):
    if cmd == "":
        print("Please enter a command")
    elif cmd == "EXIT":
        print("Closed connection")
        return False
    elif cmd == "START":
        infinite_requests()
    elif cmd.startswith("SERVER"):
        address_port = get_argument(cmd)
        connect_to_server(address_port)
    elif cmd.startswith("CLIENT"):
        address_port = get_argument(cmd)
        connect_to_client(address_port)
    elif cmd.startswith("ENTRYNUMBER"):
        entry_number = get_argument(cmd)
        set_entry_number(entry_number)
    elif cmd == "SUBMIT":
        submit_lines()
    elif cmd == "CLEAR":
        lines.clear()
        print("Cleared dictionary")
    elif cmd == "PRINT":
        print(f"Unique lines = {len(lines)}")
    elif cmd == "INCORRECT":
        get_incorrect_lines()
    elif cmd == "RESET":
        reset_session()
    else:
        print("Invalid Command")
    return True


def init():
    if OTHER_CLIENTS > 0:
        print("Created receiving sockets at ports:")
    for i in range(OTHER_CLIENTS):
        client_socket = socket.socket()
        lines_received.append(0)
        host = ""
        port = 10000 + i
        print(port, end = "")
        if i == OTHER_CLIENTS - 1:
            print()
        else:
            print(" ", end = "")
        client_socket.bind((host, port))
        client_socket.listen(5)
        receiving_client_sockets.append(client_socket)
        receiving_threads.append(threading.Thread(target = worker_function, daemon = True, args = (i,)))
        receiving_threads[i].start()


def start_command():
    try:
        while True:
            cmd = input()
            if not handle_command(cmd.strip().upper()):
                break
    except KeyboardInterrupt:
        print("\nConnection closed by user")
    finally:
        server_conn.close()
        stop_event.set()
        for sock in sending_client_sockets:
            sock.close()
        for sock in receiving_client_sockets:
            sock.close()
        print("Closed all sockets")


init()
start_command()
