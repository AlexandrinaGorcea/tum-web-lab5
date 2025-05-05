import socket
import sys
import os
from urllib.parse import urlparse

def make_http_request(host, path, port=80):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    
    try:
        s.connect((host, port))
        
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "Connection: close\r\n"
        request += "User-Agent: go2web/0.1\r\n"
        request += "\r\n"
        
        s.sendall(request.encode())
        
        # Receive the response
        chunks = []
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        
        response = b''.join(chunks).decode('utf-8', errors='replace')
        
        return response
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        s.close()

def request_url(url):
    # Check if URL has protocol, if not add http://
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    
    # Parse URL
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    if not path:
        path = "/"
    
    # Make request
    response = make_http_request(host, path)
    print(response)

def print_help():
    """Print help information"""
    print("go2web -u <URL>    # make an HTTP request to the specified URL and print the response")
    print("go2web -h          # show this help")

def main():
    args = sys.argv[1:]
    
    if not args or args[0] == '-h':
        print_help()
        return
    
    if args[0] == '-u' and len(args) > 1:
        url = args[1]
        request_url(url)
    else:
        print("Error: Invalid arguments.")
        print_help()

if __name__ == "__main__":
    main()