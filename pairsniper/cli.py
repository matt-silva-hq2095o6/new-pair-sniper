import argparse
import asyncio
import logging
import sys
from pairsniper.config import load_config
from pairsniper.watcher import run_watcher


def main():
    parser = argparse.ArgumentParser(description="tail pair creation logs on evm chains")
    parser.add_argument("-c", "--config", help="path to pairsniper.toml config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose debug logging")
    parser.add_argument("--min-liq", type=float, help="min pool eth liquidity threshold")
    args = parser.parse_args()

    lvl = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=lvl, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        cfg = load_config(args.config)
    except Exception as e:
        logging.error(f"failed to load config: {e}")
        sys.exit(1)

    if args.min_liq is not None:
        cfg.min_liquidity_eth = args.min_liq

    try:
        asyncio.run(run_watcher(cfg))
    except KeyboardInterrupt:
        logging.info("stopped by user")


if __name__ == "__main__":
    main()
