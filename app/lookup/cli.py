import argparse
import json

from app.lookup.service import PartLookupService


def main():
    parser = argparse.ArgumentParser(
        description="Check laptop spare part details from internet",
    )

    parser.add_argument("--brand", required=True)
    parser.add_argument("--part-number", required=True)
    parser.add_argument("--product-name", required=False)

    args = parser.parse_args()

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