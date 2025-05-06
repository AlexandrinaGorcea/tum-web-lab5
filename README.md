# tum-web-lab5
# go2web - Command Line Web Browser

![Go2Web Demo](https://github.com/AlexandrinaGorcea/tum-web-lab5/blob/main/go2web-demo.gif)

## Description

`go2web` is a command-line web browsing tool that allows users to make HTTP requests, search the web, and view the results in a human-readable format. This project was developed as part of a networking laboratory work to demonstrate understanding of HTTP protocols and socket programming without relying on built-in HTTP libraries.

The tool is implemented in Python but uses only the socket library for HTTP communication, ensuring a deeper understanding of the HTTP protocol. It provides a clean and user-friendly interface for browsing the web from your terminal.

## Features

- **Direct URL Access**: Make HTTP requests to any URL and view the content in a readable format
- **Web Search**: Search the web using Bing and get top 10 results
- **Search Result Access**: Directly access any search result from your search query
- **Human-Readable Output**: All HTML and JSON content is processed and displayed in a clean format
- **Help Menu**: Comprehensive help information for all commands

## Additional Implementations

- **HTTP Redirects (+1 point)**: The tool follows HTTP redirects (301, 302, 303, 307, 308) automatically
- **Search Result Access (+1 point)**: Access specific search results with the `-a` flag
- **HTTP Cache Mechanism (+2 points)**: Implemented caching system using TinyDB to store responses
- **Content Negotiation (+2 points)**: Handles both HTML and JSON content types with appropriate formatting

## Installation

Install the package:
```bash
pip install -e .
```

This will install the `go2web` command globally on your system.

## Usage

```bash
# Make an HTTP request to a URL
go2web -u example.com

# Search the web for a term
go2web -s python programming

# Search and access a specific result (e.g., the 3rd result)
go2web -s python programming -a 3

# Clear the cache
go2web -c

# Show help information
go2web -h
```

## How It Works

The tool works by:

1. Creating a raw socket connection to the target server
2. Constructing HTTP request headers manually
3. Sending the request and receiving the response
4. Parsing the response (HTML or JSON) into human-readable format
5. Displaying the formatted content to the user

## Technical Details

- **No HTTP Libraries**: Uses only socket programming for making HTTP requests
- **BeautifulSoup4**: Used for parsing HTML content
- **TinyDB**: Simple document database for caching responses
- **SSL Support**: Secured connections through the SSL library


