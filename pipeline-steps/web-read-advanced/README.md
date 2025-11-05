# web-read-advanced

Advanced web crawler with JSONPath-based result extraction and concurrent processing

## Overview

This pipeline step is an advanced web crawler that:
- Fetches JSON data from URLs with concurrent requests
- Extracts results using JSONPath templates
- Follows links to crawl additional pages
- Supports rate limiting and duplicate URL detection
- Can process both seed URLs and input files

## Docker Image

This application is available as a Docker image on Docker Hub: `pipelining/web-read-advanced`

### Usage

Basic usage with seed URLs:
```bash
docker run -v /path/to/config.json:/config.json \
           -v /path/to/output:/output \
           pipelining/web-read-advanced:latest \
           --config /config.json \
           --output /output/results.jsonl
```

With input file and Google authentication:
```bash
docker run -v /path/to/input.jsonl:/input.jsonl \
           -v /path/to/config.json:/config.json \
           -v /path/to/output:/output \
           -v /path/to/credentials.json:/credentials.json \
           -e GOOGLE_APPLICATION_CREDENTIALS=/credentials.json \
           pipelining/web-read-advanced:latest \
           --input /input.jsonl \
           --config /config.json \
           --output /output/results.jsonl
```

## Configuration Parameters

| Name            | Required | Description                                                              |
|-----------------|----------|--------------------------------------------------------------------------|
| seedUrls        | *        | List of initial URLs to crawl (required if no input file)               |
| resultTemplate  | X        | Template string with JSONPath expressions for extracting results         |
| continueTemplate|          | Template string with JSONPath expressions for extracting next URLs       |
| useGoogleToken  |          | If true, uses Google Application Default Credentials to add Bearer token |
| scopes          |          | List of OAuth scopes to request (only valid when useGoogleToken is true) |
| headers         |          | Dictionary of custom HTTP headers to include in all requests            |
| concurrency     |          | Number of concurrent worker threads (default: 1)                        |
| rateLimit       |          | Maximum requests per second across all threads (default: 10.0)          |
| queueThreshold  |          | Maximum queue size before pausing input reading (default: 100)          |
| removeDuplicates|          | If true, avoid processing the same URL twice (default: false)           |

## Input Format (Optional)

If provided, the input JSONL file should contain one JSON object per line with a `url` field:

```jsonl
{"url": "https://api.example.com/page1"}
{"url": "https://api.example.com/page2"}
```

Other fields are ignored. URLs are added to the processing queue alongside seed URLs.

## Template Syntax

Templates use `${jsonpath}` syntax to extract values from JSON responses.

### Example JSON Response
```json
{
  "data": {
    "items": [
      {"id": 1, "name": "Item 1"},
      {"id": 2, "name": "Item 2"}
    ],
    "nextPage": "https://api.example.com/page2"
  }
}
```

### Example Templates

**Result Template** (extracts multiple results):
```
{"id": ${data.items[*].id}, "name": "${data.items[*].name}"}
```
This would produce:
```
{"id": 1, "name": "Item 1"}
{"id": 2, "name": "Item 2"}
```

**Continue Template** (extracts next URL):
```
${data.nextPage}
```
This would extract: `https://api.example.com/page2`

## Configuration Example

```json
{
  "seedUrls": [
    "https://api.example.com/items?page=1"
  ],
  "resultTemplate": "{\"id\": ${items[*].id}, \"name\": \"${items[*].name}\"}",
  "continueTemplate": "${nextPageUrl}",
  "concurrency": 5,
  "rateLimit": 10.0,
  "removeDuplicates": true,
  "queueThreshold": 100,
  "useGoogleToken": false,
  "headers": {
    "User-Agent": "WebCrawler/1.0"
  }
}
```

## How It Works

1. **Initialization**: URL queue is populated with seed URLs and/or URLs from input file
2. **Concurrent Processing**: Multiple worker threads fetch URLs from the queue concurrently
3. **Rate Limiting**: All threads respect a global rate limit
4. **Result Extraction**: JSONPath expressions in `resultTemplate` extract data from responses
5. **Link Following**: JSONPath expressions in `continueTemplate` extract URLs for further crawling
6. **Queue Management**: Input reading pauses when queue reaches threshold
7. **Duplicate Detection**: Optional tracking of already-processed URLs
8. **Output**: Results are written to JSONL output file (thread-safe)

## Key Features

- **Concurrent Processing**: Multiple threads process URLs in parallel
- **Rate Limiting**: Global rate limit across all threads prevents overwhelming servers
- **JSONPath Extraction**: Flexible result and URL extraction using JSONPath
- **Duplicate Detection**: Optional tracking to avoid reprocessing URLs
- **Queue Management**: Threshold-based input loading prevents memory issues
- **Thread-Safe Output**: Synchronized writing to output file
- **Google Authentication**: Optional OAuth token support for Google APIs
- **Custom Headers**: Add any HTTP headers to requests

## Notes

* **seedUrls**: At least one of `seedUrls` or input file must be provided
* **resultTemplate**: Can extract multiple results per response using JSONPath wildcards
* **continueTemplate**: Can extract multiple URLs per response for pagination/crawling
* **concurrency**: Higher values increase speed but also resource usage
* **rateLimit**: Set to 0 for no rate limiting (use with caution)
* **removeDuplicates**: Useful for crawling but increases memory usage for large crawls
* **useGoogleToken**: Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
* **scopes**: Only valid when useGoogleToken is true
* **headers**: Custom Authorization header conflicts with useGoogleToken

## Performance Tuning

- **Increase concurrency** for faster crawling (but respect server limits)
- **Adjust rateLimit** to match API rate limits
- **Set queueThreshold** based on available memory
- **Enable removeDuplicates** for graph-like link structures
- **Disable removeDuplicates** for simple pagination to save memory
