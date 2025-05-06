import socket
import sys
import os
import ssl
from urllib.parse import urlparse

def parse_http_response(response):
    """Parse HTTP response into headers and body"""
    # Split response into headers and body
    parts = response.split("\r\n\r\n", 1)
    if len(parts) < 2:
        return None, response
    
    headers_raw = parts[0]
    body = parts[1]
    
    # Parse headers
    headers = {}
    for line in headers_raw.split("\r\n")[1:]:  # Skip status line
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    
    return headers, body

def extract_status_code(response):
    """Extract HTTP status code from response"""
    first_line = response.split('\r\n')[0]
    parts = first_line.split(' ')
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None

def is_redirect(status_code):
    """Check if status code is a redirect code"""
    return status_code in [301, 302, 303, 307, 308]

def make_http_request(host, path, port=80, use_ssl=False):
    """Make a basic HTTP request without built-in HTTP libraries"""
    # Create a socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    
    try:
        # Wrap socket with SSL if needed
        if use_ssl:
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            s = context.wrap_socket(s, server_hostname=host)
        
        # Connect to host
        s.connect((host, port))
        
        # Prepare the request
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "Connection: close\r\n"
        request += "User-Agent: go2web/0.1\r\n"
        request += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
        request += "\r\n"
        
        # Send the request
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
    except socket.timeout:
        return f"Error: Connection timed out to {host}"
    except socket.gaierror:
        return f"Error: Could not resolve hostname: {host}"
    except ConnectionRefusedError:
        return f"Error: Connection refused by {host}:{port}"
    except ssl.SSLError as e:
        return f"Error: SSL Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        s.close()

def request_url(url, follow_redirects=True):
    """Make an HTTP request to the specified URL"""
    # Check if URL has protocol, if not add http://
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    
    # Parse URL
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path
    if not path:
        path = "/"
    if parsed_url.query:
        path += "?" + parsed_url.query
    
    # Set up port and SSL
    use_ssl = parsed_url.scheme == 'https'
    if parsed_url.port:
        port = parsed_url.port
    elif use_ssl:
        port = 443
    else:
        port = 80
    
    # Make request
    response = make_http_request(host, path, port, use_ssl)
    
    # Handle redirects
    if follow_redirects:
        status_code = extract_status_code(response)
        if status_code and is_redirect(status_code):
            headers, _ = parse_http_response(response)
            if headers and 'location' in headers:
                new_url = headers['location']
                # Handle relative URLs
                if not new_url.startswith('http'):
                    scheme = parsed_url.scheme or 'http'
                    if new_url.startswith('/'):
                        new_url = f"{scheme}://{host}{new_url}"
                    else:
                        new_url = f"{scheme}://{host}/{new_url}"
                print(f"Redirecting to: {new_url}")
                return request_url(new_url, follow_redirects)
    
    # Process response
    headers, body = parse_http_response(response)
    
    if headers:
        print("--- Response Headers ---")
        for key, value in headers.items():
            print(f"{key}: {value}")
        print("\n--- Response Body ---")
    
    print(body)

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