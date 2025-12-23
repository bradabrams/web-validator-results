#!/usr/bin/env python3
"""
local_proxy.py - Local proxy adapter that handles JWT auth for browsers in sandbox.

This proxy sits between Playwright and the sandbox's JWT-authenticated proxy,
automatically adding the Proxy-Authorization header that browsers can't handle.

Usage:
    python local_proxy.py &
    # Then configure Playwright to use http://127.0.0.1:8888 as proxy
"""
import os
import socket
import threading
import base64
import re
import sys

# Parse proxy settings from environment
HTTPS_PROXY = os.environ.get('HTTPS_PROXY', os.environ.get('https_proxy', ''))
proxy_match = re.match(r'https?://([^:]+):([^@]+)@([^:]+):(\d+)', HTTPS_PROXY)
if proxy_match:
    PROXY_USER, PROXY_PASS = proxy_match.group(1), proxy_match.group(2)
    REAL_PROXY_HOST, REAL_PROXY_PORT = proxy_match.group(3), int(proxy_match.group(4))
else:
    PROXY_USER = PROXY_PASS = ""
    REAL_PROXY_HOST, REAL_PROXY_PORT = "127.0.0.1", 8080

LOCAL_PORT = 8888


def get_proxy_auth():
    """Get base64-encoded proxy authorization."""
    if PROXY_USER and PROXY_PASS:
        return base64.b64encode(f"{PROXY_USER}:{PROXY_PASS}".encode()).decode()
    return None


def handle_client(client_socket):
    """Handle a client connection."""
    try:
        request = client_socket.recv(8192).decode('utf-8', errors='ignore')
        if not request:
            return
        parts = request.split('\n')[0].split()
        if len(parts) < 2:
            return
        method = parts[0]

        if method == 'CONNECT':
            # HTTPS tunnel request
            host_port = parts[1]
            host, port = (host_port.rsplit(':', 1) + ['443'])[:2]
            port = int(port) if ':' in host_port else 443

            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.settimeout(30)
            proxy_socket.connect((REAL_PROXY_HOST, REAL_PROXY_PORT))

            # Send CONNECT with auth to real proxy
            connect_request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            auth = get_proxy_auth()
            if auth:
                connect_request += f"Proxy-Authorization: Basic {auth}\r\n"
            connect_request += "\r\n"
            proxy_socket.send(connect_request.encode())

            response = proxy_socket.recv(4096).decode('utf-8', errors='ignore')
            if '200' in response.split('\n')[0]:
                # Tunnel established, tell client
                client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                client_socket.setblocking(False)
                proxy_socket.setblocking(False)

                # Relay data between client and proxy
                def relay(src, dst):
                    try:
                        while True:
                            try:
                                data = src.recv(65536)
                                if not data:
                                    break
                                dst.sendall(data)
                            except BlockingIOError:
                                pass
                            except:
                                break
                    except:
                        pass

                t1 = threading.Thread(target=relay, args=(client_socket, proxy_socket), daemon=True)
                t2 = threading.Thread(target=relay, args=(proxy_socket, client_socket), daemon=True)
                t1.start()
                t2.start()
                t1.join(timeout=60)
                t2.join(timeout=60)
            else:
                client_socket.send(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{response}".encode())
            proxy_socket.close()
        else:
            # Regular HTTP request
            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.settimeout(30)
            proxy_socket.connect((REAL_PROXY_HOST, REAL_PROXY_PORT))
            auth = get_proxy_auth()
            if auth and 'Proxy-Authorization' not in request:
                lines = request.split('\r\n')
                lines.insert(1, f"Proxy-Authorization: Basic {auth}")
                request = '\r\n'.join(lines)
            proxy_socket.send(request.encode())
            while True:
                try:
                    data = proxy_socket.recv(8192)
                    if not data:
                        break
                    client_socket.send(data)
                except:
                    break
            proxy_socket.close()
    except Exception as e:
        print(f"Error handling client: {e}", file=sys.stderr)
    finally:
        try:
            client_socket.close()
        except:
            pass


def main():
    """Start the local proxy server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', LOCAL_PORT))
    server.listen(10)
    print(f"Local proxy listening on 127.0.0.1:{LOCAL_PORT}")
    print(f"Real proxy: {REAL_PROXY_HOST}:{REAL_PROXY_PORT}")
    print(f"Auth configured: {'Yes' if PROXY_USER else 'No'}")
    sys.stdout.flush()

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error accepting connection: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
