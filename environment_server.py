from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
import struct
import json
from io import BytesIO
from threading import Thread, RLock
from subprocess import Popen, DEVNULL


server_port = 11000

next_mlagents_port = 11001
next_mlagents_port_lock = RLock()


def forward_data(fromsocket: socket, tosocket: socket):
    try:
        while True:
            data = fromsocket.recv(4096)
            if len(data) == 0:
                break
            data = bytearray(data)
            tosocket.sendall(data)
    except:
        pass
    finally:
        print("Forward thread ended")
        fromsocket.close()
        tosocket.close()


def handle_client(client_socket: socket, addr):
    buf = BytesIO()

    while buf.tell() < 4:
        b = client_socket.recv(4 - buf.tell())
        buf.write(b)
    buf.seek(0)
    json_string_length_bytes = buf.read()

    if len(json_string_length_bytes) != 4:
        print("Length of json string length was not 4 ({})".format(len(json_string_length_bytes)))
        client_socket.close()
        return

    (json_string_length,) = struct.unpack(">i", json_string_length_bytes)
    print("Json string length is", json_string_length)
    buf.seek(0)
    while buf.tell() < json_string_length:
        buf.write(client_socket.recv(json_string_length - buf.tell()))

    buf.seek(0)
    json_string = buf.read().decode("utf-8")
    args = json.loads(json_string)

    if len(args) < 1:
        print("No env specified. Closing connection. (Args length was 0)")
        client_socket.close()
        return

    env = args[0]
    env_args = args[1:]
    print(f"Env is {env}, env-args is {env_args}")
    # we need to override the -logFile
    next_mlagents_port_lock.acquire()
    global next_mlagents_port
    PORT_NUM = next_mlagents_port
    next_mlagents_port += 1
    next_mlagents_port_lock.release()

    for i in range(len(env_args)):
        if env_args[i] == "--mlagents-port":
            env_args[i+1] = str(PORT_NUM)
            print("Overwrote port number")
        if env_args[i] == "-logFile":
            env_args[i+1] = "log.log"
            print("Overwrote log filename")


    if "--mlagents-port" not in env_args:
        args.extend(["--mlagents-port", PORT_NUM])

    # start the environment

    path = env + "LearningUnity.exe"

    env_server_socket = socket(AF_INET, SOCK_STREAM)
    env_server_socket.bind(("localhost", PORT_NUM))
    env_server_socket.listen()
    print(f"Listening for {path} on port {PORT_NUM}")
    p = None
    try:
        p_open_args = [path] + env_args
        print("Popen args", p_open_args)
        p = Popen(p_open_args, stdout=DEVNULL)
        env_socket, addr = env_server_socket.accept()
        Thread(target=forward_data, args=(env_socket, client_socket)).start()
        forward_data(client_socket, env_socket)
    finally:
        env_server_socket.shutdown(SHUT_RDWR)
        env_server_socket.close()
        client_socket.shutdown(SHUT_RDWR)
        client_socket.close()
        print(f"Env on port {PORT_NUM} terminated.")
        if p is not None:
            p.kill()


def main():
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind(("0.0.0.0", server_port))
    print(f"Environment server listening on port {server_port}")
    server_socket.listen()

    while True:
        client_socket, addr = server_socket.accept()
        print("Incoming connection from", addr)
        Thread(target=handle_client, args=(client_socket, addr)).start()


if __name__ == "__main__":
    main()
