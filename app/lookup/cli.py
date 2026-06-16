import argparse
import json

from app.lookup.search import WebSearchClient
from app.lookup.service import PartLookupService


def main():
    parser = argparse.ArgumentParser(
        description="Check spare part details from internet",
    )

    parser.add_argument("--brand", required=True)
    parser.add_argument("--part-number", required=True)
    parser.add_argument("--product-name", required=False)
    parser.add_argument("--debug-search", action="store_true")

    args = parser.parse_args()

    if args.debug_search:
        search_client = WebSearchClient()

        results = search_client.search_part(
            brand_name=args.brand,
            part_number=args.part_number,
            product_name=args.product_name,
        )

        print(
            json.dumps(
                [item.model_dump() for item in results],
                indent=2,
                default=str,
            )
        )

        return

    service = PartLookupService()

    if args.product_name:
        result = service.lookup_market_price(
            brand_name=args.brand,
            part_number=args.part_number,
            product_name=args.product_name,
        )
    else:
        result = service.lookup_new_part(
            brand_name=args.brand,
            part_number=args.part_number,
        )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()