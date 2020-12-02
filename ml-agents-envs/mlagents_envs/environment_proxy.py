import struct
import json

from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from threading import Thread
from os import getenv

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


def create_env_proxy(local_port, env_args):
    def target():
        env_server_sock = socket(AF_INET, SOCK_STREAM)
        env_server_ip = getenv("ENV_SERVER_IP", "localhost")
        env_server_port = int(getenv("ENV_SERVER_PORT", 11000))
        print(f"Attempting to connect to env server at {env_server_ip}:{env_server_port}")
        env_server_sock.connect((env_server_ip, env_server_port))

        # First send the environment args
        env_args_bytes = json.dumps(env_args).encode("utf-8")
        env_args_bytes_length = len(env_args_bytes)
        env_args_bytes_length_encoded = struct.pack(">i", env_args_bytes_length)
        env_server_sock.sendall(env_args_bytes_length_encoded)
        env_server_sock.sendall(env_args_bytes)

        trainer_socket = socket(AF_INET, SOCK_STREAM)
        trainer_socket.connect(("localhost", local_port))
        try:
            Thread(target=forward_data, args=(trainer_socket, env_server_sock)).start()
            forward_data(env_server_sock, trainer_socket)
        finally:
            trainer_socket.shutdown(SHUT_RDWR)
            trainer_socket.close()
            env_server_sock.shutdown(SHUT_RDWR)
            env_server_sock.close()

    Thread(target=target).start()






