import multiprocessing
import subprocess
import os
import socket
import clipboard
import time
import struct


def pinger(job_q, results_q):
    """
    Do Ping
    :param job_q:
    :param results_q:
    :return:
    """
    devnull = open(os.devnull, 'w')
    while True:

        ip = job_q.get()

        if ip is None:
            break

        try:
            subprocess.check_call(['ping', '-c1', ip],
                                  stdout=devnull)
            results_q.put(ip)
        except:
            pass


def get_my_ip():
    """
    Find my IP address
    :return:
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
    sock.close()
    return ip


def map_network(pool_size=255):
    """
    Maps the network
    :param pool_size: amount of parallel ping processes
    :return: list of valid ip addresses
    """

    ip_list = list()

    # get my IP and compose a base like 192.168.1.xxx
    ip_parts = get_my_ip().split('.')
    base_ip = ip_parts[0] + '.' + ip_parts[1] + '.' + ip_parts[2] + '.'

    # prepare the jobs queue
    jobs = multiprocessing.Queue()
    results = multiprocessing.Queue()

    pool = [multiprocessing.Process(target=pinger, args=(jobs, results)) for y in range(pool_size)]

    for p in pool:
        p.start()

    # cue hte ping processes
    for pp in range(1, 255):
        jobs.put(base_ip + '{0}'.format(pp))

    for p in pool:
        jobs.put(None)

    for p in pool:
        p.join()

    # collect he results
    while not results.empty():
        ip = results.get()
        remoteserver = str(ip)
        remoteserverip = socket.gethostbyname(remoteserver)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((remoteserverip, 65432))
        if result == 0:
            ip_list.append(ip)

    return ip_list


def send_msg(sock, msg):
    # Prefix each message with a 4-byte length (network byte order)
    msg = struct.pack('>I', len(msg)) + msg
    sock.sendall(msg)


def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)


def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    dat = bytearray()
    while len(dat) < n:
        packet = sock.recv(n - len(dat))
        if not packet:
            return None
        dat.extend(packet)
    return dat


if __name__ == '__main__':
    k = input('Broadcast clipboard or receive it? (0 to broadcast 1 to receive)\n')
    if k == '0':
        print('This is your local IP address: ' + str(get_my_ip()))
        while True:
            print('Manually type the client IP address or use network discovery? (0 or 1)')
            choice = int(input())
            if choice == 0:
                HOST = str(input())
            else:
                while True:
                    print('Searching for devices to broadcast to...')
                    u = map_network()
                    if len(u) == 0:
                        print('No device was found, make sure to run the program in your other device\n'
                              'and then hit enter:')
                        input()
                    else:
                        break
                print('Choose the client side number from this list:')
                for i in range(len(u)):
                    print(str(i) + ' ' + str(u[i]))
                HOST = u[int(input())]
            PORT = 65432  # The port used by the server
            cur = str(clipboard.paste())
            # Checking change in the clipboard
            while True:
                new = str(clipboard.paste())
                # If there is change, update the client device
                if new != cur:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((HOST, PORT))
                            send_msg(s, str.encode(new))
                        cur = new
                    except ConnectionRefusedError:
                        # If the client side is down, either change client or try again
                        print(
                            'Client side refused connection, make sure the program is up and running in it, then try '
                            'again.')
                        print("If you'd like to change the client device"
                              " enter 1, or enter anything else to keep the current client.")
                        choice = int(input())
                        if choice == 1:
                            break
                # 1 second cool down
                time.sleep(1)
    if k == '1':
        HOST = get_my_ip()
        PORT = 65432
        print('Waiting for a host device to share their clipboard')
        print('This is your local IP address, select it from the other device: ' + str(HOST))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            while True:
                s.listen()
                conn, addr = s.accept()
                with conn:
                    while True:
                        data = recv_msg(conn)
                        if not data:
                            break
                        print(data.decode('utf-8'))
                        clipboard.copy(data.decode('utf-8'))
