"""Multi-threaded web crawler with JSONPath-based result extraction."""

import sys
import time
import threading
from queue import Queue, Empty
from typing import List, Set, Optional

import requests
from steputil import StepArgs

from .rate_limiter import RateLimiter
from .template_resolver import TemplateResolver


class WebCrawler:
    """Multi-threaded web crawler with JSONPath-based result extraction."""

    def __init__(self, step: StepArgs, headers: dict):
        """
        Initialize the web crawler.

        Args:
            step: StepArgs containing configuration and I/O
            headers: HTTP headers to use for all requests
        """
        self.step = step
        self.headers = headers

        # Configuration
        self.result_template = step.config.resultTemplate
        self.continue_template = step.config.continueTemplate if step.config.continueTemplate else None
        self.concurrency = step.config.concurrency if step.config.concurrency else 1
        self.rate_limit = step.config.rateLimit if step.config.rateLimit else 10.0
        self.queue_threshold = step.config.queueThreshold if step.config.queueThreshold else 100
        self.remove_duplicates = step.config.removeDuplicates if step.config.removeDuplicates else False

        # State
        self.url_queue = Queue()
        self.seen_urls: Optional[Set[str]] = set() if self.remove_duplicates else None
        self.results = []
        self.results_lock = threading.Lock()
        self.rate_limiter = RateLimiter(self.rate_limit)
        self.stop_event = threading.Event()

        # Statistics
        self.processed_count = 0
        self.error_count = 0
        self.stats_lock = threading.Lock()

    def add_url(self, url: str):
        """
        Add a URL to the queue, respecting duplicate checking.

        Args:
            url: URL to add to the processing queue
        """
        if not url:
            return

        if self.remove_duplicates:
            if url in self.seen_urls:
                return
            self.seen_urls.add(url)

        self.url_queue.put(url)

    def process_url(self, url: str):
        """
        Process a single URL - fetch, extract results and continue URLs.

        Args:
            url: URL to process
        """
        try:
            # Respect rate limit
            self.rate_limiter.acquire()

            # Fetch URL
            response = requests.get(url, headers=self.headers)

            if response.status_code != 200:
                print(f"Error fetching {url}: {response.status_code}", file=sys.stderr)
                with self.stats_lock:
                    self.error_count += 1
                return

            # Parse JSON response
            try:
                data = response.json()
            except Exception as e:
                print(f"Error parsing JSON from {url}: {e}", file=sys.stderr)
                with self.stats_lock:
                    self.error_count += 1
                return

            # Extract results
            result_lines = TemplateResolver.resolve(self.result_template, data)
            if result_lines:
                with self.results_lock:
                    self.results.extend(result_lines)

            # Extract continue URLs
            if self.continue_template:
                continue_urls = TemplateResolver.resolve(self.continue_template, data)
                for continue_url in continue_urls:
                    self.add_url(continue_url)

            with self.stats_lock:
                self.processed_count += 1

        except Exception as e:
            print(f"Error processing URL {url}: {e}", file=sys.stderr)
            with self.stats_lock:
                self.error_count += 1

    def worker(self):
        """Worker thread that processes URLs from the queue."""
        while not self.stop_event.is_set():
            try:
                url = self.url_queue.get(timeout=1)
                self.process_url(url)
                self.url_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}", file=sys.stderr)

    def load_input(self):
        """
        Load URLs from input file, respecting queue threshold.

        Reads the input file progressively, pausing when the queue
        reaches the configured threshold to prevent memory issues.
        """
        if not self.step.input:
            return

        try:
            records = self.step.input.readJsons()
            print(f"Loading {len(records)} URLs from input file...")

            for record in records:
                # Wait if queue is too large
                while self.url_queue.qsize() >= self.queue_threshold:
                    if self.stop_event.is_set():
                        return
                    time.sleep(0.5)

                url = record.get('url')
                if url:
                    self.add_url(url)

            print(f"Finished loading input URLs")
        except Exception as e:
            print(f"Error loading input: {e}", file=sys.stderr)

    def crawl(self) -> List[str]:
        """
        Main crawling process.

        Starts worker threads, loads input, and processes URLs until
        the queue is empty.

        Returns:
            List of extracted result strings
        """
        # Initialize queue with seed URLs
        seed_urls = self.step.config.seedUrls if self.step.config.seedUrls else []
        print(f"Starting crawl with {len(seed_urls)} seed URLs, concurrency={self.concurrency}, rate limit={self.rate_limit} req/s")

        for url in seed_urls:
            self.add_url(url)

        # Start input loading in separate thread
        input_thread = threading.Thread(target=self.load_input, daemon=True)
        input_thread.start()

        # Start worker threads
        workers = []
        for i in range(self.concurrency):
            worker = threading.Thread(target=self.worker, daemon=True)
            worker.start()
            workers.append(worker)

        # Wait for queue to be empty
        try:
            while True:
                self.url_queue.join()
                # Double check after a short delay
                time.sleep(1)
                if self.url_queue.empty():
                    break
        except KeyboardInterrupt:
            print("Crawl interrupted by user", file=sys.stderr)

        # Stop workers
        self.stop_event.set()
        for worker in workers:
            worker.join(timeout=5)

        print(f"Crawl complete: processed {self.processed_count} URLs, {self.error_count} errors, {len(self.results)} results")

        return self.results
