import socket
import sys
import os
import ssl
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

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
        request += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\r\n"
        request += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
        request += "Accept-Language: en-US,en;q=0.9\r\n"
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

def extract_content_from_html(html):
    """Extract meaningful content from HTML using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        all_content = []
        
        # Extract title
        if soup.title:
            all_content.append(f"---- {soup.title.text.strip()}")
        
        # Extract headings
        for i in range(1, 4):  # h1, h2, h3
            for heading in soup.find_all(f'h{i}'):
                all_content.append(f"---- {heading.text.strip()}")
        
        # Extract paragraphs
        for p in soup.find_all('p'):
            text = p.text.strip()
            if text:  # Only add non-empty paragraphs
                all_content.append(f"- {text}")
        
        # Extract links
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.text.strip()
            
            # Only process http/https links
            if href.startswith('http'):
                if text:
                    links.append(f"{text}: {href}")
                else:
                    links.append(href)
        
        # Add links section
        if links:
            all_content.append("-- Links --")
            all_content.extend(links[:20])  # Limit to 20 links to avoid overwhelming output
        
        # If no meaningful content was extracted, provide a message
        if not all_content:
            all_content = ["No meaningful content could be extracted from this page.", 
                          "The page might require JavaScript or be protected against scraping."]
        
        return all_content
    except Exception as e:
        return [f"Error parsing HTML content: {str(e)}"]

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
    
    if not headers:
        print(f"Error: Invalid response format: {response[:200]}...")
        return
    
    # Extract and print content based on content type
    content_type = headers.get('content-type', '').lower()
    
    if 'text/html' in content_type:
        # Extract useful content from HTML
        content = extract_content_from_html(body)
        print(f"Information from {url}:")
        for line in content:
            print(line)
    else:
        # Just print the raw content for non-HTML responses
        print(f"Content from {url} (Content-Type: {content_type}):")
        print(body[:4000])  # Limit output to first 4000 chars
        if len(body) > 4000:
            print("... (output truncated)")

def search(term):
    """Search using DuckDuckGo and return results"""
    search_term = quote_plus(term)
    
    # Use the lite version of DuckDuckGo which is more reliable for scraping
    url = f"https://lite.duckduckgo.com/lite?q={search_term}"
    
    # Make request
    response = make_http_request("lite.duckduckgo.com", f"/lite?q={search_term}", port=443, use_ssl=True)
    
    # Extract search results using BeautifulSoup
    try:
        headers, body = parse_http_response(response)
        soup = BeautifulSoup(body, 'html.parser')
        results = []
        
        # DuckDuckGo lite uses a simple table structure
        for i, tr in enumerate(soup.find_all('tr', class_='result-item')):
            if i >= 10:  # Limit to 10 results
                break
                
            try:
                # Find link and snippet
                link_elem = tr.find('a', class_='result-link') or tr.find('a')
                snippet_elem = tr.find(class_='result-snippet') or tr.find_next_sibling('tr')
                
                if link_elem:
                    title = link_elem.text.strip()
                    href = link_elem.get('href', '')
                    
                    # Extract snippet if available
                    snippet = ""
                    if snippet_elem:
                        snippet = snippet_elem.text.strip()
                    
                    results.append(f"{i+1}. {title}\n   {href}\n   {snippet}")
            except Exception as e:
                print(f"Error processing search result {i+1}: {str(e)}")
        
        # If no results found, provide a message
        if not results:
            results = ["No search results found. Please try a different search term."]
        
        return results
        
    except Exception as e:
        return [f"Error parsing search results: {str(e)}. Please try a different search term."]

def print_help():
    """Print help information"""
    print("go2web -u <URL>                # make an HTTP request to the specified URL and print the response")
    print("go2web -s <search-term>        # search the term and print results")
    print("go2web -h                      # show this help")

def main():
    args = sys.argv[1:]
    
    if not args or args[0] == '-h':
        print_help()
        return
    
    if args[0] == '-u' and len(args) > 1:
        url = args[1]
        request_url(url)
    elif args[0] == '-s' and len(args) > 1:
        search_term = " ".join(args[1:])
        print(f"Search results for '{search_term}':")
        results = search(search_term)
        for result in results:
            print(result)
            print()
    else:
        print("Error: Invalid arguments.")
        print_help()

if __name__ == "__main__":
    main()