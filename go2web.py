import socket
import sys
import os
import time
import ssl
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query

# Cache mechanism using TinyDB
CACHE_DIR = ".go2web_cache"
CACHE_DB = "go2web_cache.json"
CACHE_DURATION = 3600  # 1 hour in seconds

def setup_cache():
    """Create cache directory if it doesn't exist"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    return TinyDB(os.path.join(CACHE_DIR, CACHE_DB))

def get_from_cache(url):
    """Get response from cache if valid"""
    db = setup_cache()
    Cache = Query()
    result = db.search((Cache.url == url) & (Cache.timestamp > time.time() - CACHE_DURATION))
    if result:
        return result[0]['content']
    return None

def save_to_cache(url, content):
    """Save response to cache"""
    db = setup_cache()
    Cache = Query()
    # Update or insert
    db.upsert(
        {'url': url, 'content': content, 'timestamp': time.time()},
        Cache.url == url
    )

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

def make_http_request(host, path, headers=None, port=80, use_ssl=False):
    """Make a basic HTTP request without built-in HTTP libraries"""
    if headers is None:
        headers = {}
    
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
        request += "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n"
        request += "Accept-Language: en-US,en;q=0.9\r\n"
        request += "Accept-Encoding: identity\r\n"
        request += "Upgrade-Insecure-Requests: 1\r\n"
        
        # Add custom headers
        for key, value in headers.items():
            request += f"{key}: {value}\r\n"
        
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
    except ConnectionResetError:
        return f"Error: Connection reset by peer"
    except ssl.SSLError as e:
        return f"Error: SSL Error: {str(e)}"
    finally:
        s.close()

def format_json(data, prefix="", max_depth=3, current_depth=0):
    """Format JSON data for human-readable output"""
    result = []
    
    # Prevent going too deep in nested structures
    if current_depth >= max_depth:
        return [f"{prefix}[Complex nested data]"]
    
    if isinstance(data, dict):
        # Handle dictionaries (JSON objects)
        if current_depth == 0:
            result.append("JSON Content:")
        
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(f"{prefix}--- {key} ---")
                result.extend(format_json(value, prefix + "  ", max_depth, current_depth + 1))
            elif isinstance(value, list):
                if not value:
                    result.append(f"{prefix}- {key}: []")
                else:
                    result.append(f"{prefix}- {key}: [Array with {len(value)} items]")
                    result.extend(format_json(value, prefix + "  ", max_depth, current_depth + 1))
            else:
                result.append(f"{prefix}- {key}: {value}")
    
    elif isinstance(data, list):
        # Handle lists (JSON arrays)
        if current_depth == 0:
            result.append("JSON Content: [Array]")
        
        # Limit the number of items shown
        display_limit = 10
        
        for i, item in enumerate(data[:display_limit]):
            if isinstance(item, (dict, list)):
                result.append(f"{prefix}Item {i+1}:")
                result.extend(format_json(item, prefix + "  ", max_depth, current_depth + 1))
            else:
                result.append(f"{prefix}Item {i+1}: {item}")
        
        if len(data) > display_limit:
            result.append(f"{prefix}... and {len(data) - display_limit} more items")
    
    else:
        # Handle primitive types (strings, numbers, booleans, null)
        result.append(f"{prefix}{data}")
    
    return result

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

def request_url(url, follow_redirects=True, accept_header=None):
    """Make an HTTP request to the specified URL"""
    # Check if URL has protocol, if not add http://
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    
    # Check cache first
    cached_content = get_from_cache(url)
    if cached_content:
        return cached_content
    
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
    
    # Set headers
    headers = {}
    if accept_header:
        headers['Accept'] = accept_header
    
    # Make request
    response = make_http_request(host, path, headers, port, use_ssl)
    
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
                return request_url(new_url, follow_redirects, accept_header)
    
    # Process response
    headers, body = parse_http_response(response)
    
    if not headers:
        return [f"Error: Invalid response format: {response[:200]}..."]
    
    # Handle content negotiation
    content_type = headers.get('content-type', '').lower() if headers else ''
    
    # Process response based on content type
    if 'application/json' in content_type or (body.strip().startswith('{') and body.strip().endswith('}')):
        try:
            import json
            data = json.loads(body)
            return format_json(data)
        except json.JSONDecodeError as e:
            return [f"Error parsing JSON content: {str(e)}"]
    else:
        # Extract useful content from HTML using BeautifulSoup
        result = extract_content_from_html(body)
    
    # Cache the processed content
    save_to_cache(url, result)
    
    return result

def search(term):
    """Search Bing and return top 10 results"""
    search_term = quote_plus(term)
    url = f"https://www.bing.com/search?q={search_term}"

    # Make the HTTP request
    response = make_http_request("www.bing.com", f"/search?q={search_term}", port=443, use_ssl=True)

    try:
        headers, body = parse_http_response(response)
        soup = BeautifulSoup(body, 'html.parser')
        results = []
        urls = []

        # Attempt to parse Bing results
        result_blocks = soup.select('li.b_algo')
        for i, result in enumerate(result_blocks[:10]):
            title_elem = result.find('h2')
            link_elem = title_elem.find('a') if title_elem else None

            if title_elem and link_elem:
                title = title_elem.text.strip()
                link = link_elem.get('href')
                results.append(f"{i+1}. {title}\n   {link}")
                urls.append(link)

        if not results:
            results = ["No search results found. Please try a different search term."]

        save_to_cache(url, {"results": results, "urls": urls})
        return {"results": results, "urls": urls}

    except Exception as e:
        error_message = [f"Error parsing Bing search results: {str(e)}."]
        save_to_cache(url, {"results": error_message, "urls": []})
        return {"results": error_message, "urls": []}

def print_help():
    """Print help information"""
    print("go2web -u <URL>                # make an HTTP request to the specified URL and print the response")
    print("go2web -s <search-term>        # search the term and print top 10 results")
    print("go2web -h                      # show this help")

def main():
    args = sys.argv[1:]
    
    if not args or args[0] == '-h':
        print_help()
        return
    
    if args[0] == '-u' and len(args) > 1:
        url = args[1]
        response = request_url(url)
        print(f"Information from {url}:")
        for line in response:
            print(line)
    
    elif args[0] == '-s' and len(args) > 1:
        search_term = " ".join(args[1:])
        print(f"Search results for '{search_term}':")
        search_data = search(search_term)
        for result in search_data["results"]:
            print(result)
            print()
        
    else:
        print("Error: Invalid arguments.")
        print_help()

if __name__ == "__main__":
    main()