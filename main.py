import argparse

from playwright_crawler import main as crawl_main


def parse_args():
    parser = argparse.ArgumentParser(description="Async Playwright career crawler")
    parser.add_argument(
        "--domains-file",
        default="domains.txt",
        help="Path to newline-delimited domains to crawl",
    )
    parser.add_argument(
        "--output",
        default="results.jsonl",
        help="Path to JSONL output file",
    )
    return parser.parse_args()


def run():
    args = parse_args()
    crawl_main(args.domains_file, args.output)


if __name__ == "__main__":
    run()
