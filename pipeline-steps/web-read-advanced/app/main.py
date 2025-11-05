"""Main entry point for web-read-advanced pipeline step."""

import sys
import os
import json
from steputil import StepArgs, StepArgsBuilder

# Import modules from same directory
from auth import get_access_token
from crawler import WebCrawler


def main(step: StepArgs):
    """
    Main processing function for the web crawler.

    Args:
        step: StepArgs containing configuration, input, and output
    """
    # Prepare headers - start with custom headers if provided
    headers = {}
    if step.config.headers:
        headers.update(step.config.headers)
        print(f"Using custom headers: {list(step.config.headers.keys())}")

    # Optionally add Google authentication
    if step.config.useGoogleToken:
        print("Getting credentials from Application Default Credentials (ADC)")
        scopes = step.config.scopes if step.config.scopes else []
        token = get_access_token(scopes)
        headers['Authorization'] = f'Bearer {token}'
        print(f"Added Bearer token to request headers")

    # Create crawler and run
    crawler = WebCrawler(step, headers)
    results = crawler.crawl()

    # Write results as JSONL (each result line as a JSON string)
    output_records = []
    for result_line in results:
        # Try to parse as JSON, otherwise store as string
        try:
            result_obj = json.loads(result_line)
            output_records.append(result_obj)
        except:
            # If not valid JSON, wrap in object
            output_records.append({"result": result_line})

    step.output.writeJsons(output_records)
    print(f"Written {len(output_records)} results to output")


def validate_config(config):
    """
    Validation function that checks config rules.

    Args:
        config: Configuration object to validate

    Returns:
        True if valid, False otherwise
    """
    # Check that scopes is only used when useGoogleToken is true
    if config.scopes and not config.useGoogleToken:
        print("Parameter `scopes` can only be used when `useGoogleToken` is true", file=sys.stderr)
        return False

    # Check that Authorization header doesn't conflict with useGoogleToken
    if config.useGoogleToken and config.headers:
        if 'Authorization' in config.headers:
            print("Cannot use `useGoogleToken` when custom `Authorization` header is provided in `headers`", file=sys.stderr)
            return False

    # Check that resultTemplate is provided
    if not config.resultTemplate:
        print("Parameter `resultTemplate` is required", file=sys.stderr)
        return False

    # Check that at least seedUrls or input is provided
    seed_urls = config.seedUrls if config.seedUrls else []
    if not seed_urls and not hasattr(config, '_has_input'):
        print("Either `seedUrls` or input file must be provided", file=sys.stderr)
        return False

    return True


if __name__ == "__main__":
    main(StepArgsBuilder()
         .input(optional=True)
         .output()
         .config("seedUrls", optional=True)
         .config("resultTemplate")
         .config("continueTemplate", optional=True)
         .config("useGoogleToken", optional=True)
         .config("scopes", optional=True)
         .config("headers", optional=True)
         .config("concurrency", optional=True)
         .config("rateLimit", optional=True)
         .config("queueThreshold", optional=True)
         .config("removeDuplicates", optional=True)
         .validate(validate_config)
         .build()
         )
