"""Probe de disponibilité gRPC utilisable par Docker Compose."""
import argparse
import os

from grpc_services.clients import check_health


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("pharmacie", "radiologie"))
    args = parser.parse_args()
    variable, fallback = (
        ("PHARMACIE_GRPC_TARGET", "localhost:50052")
        if args.service == "pharmacie"
        else ("RADIOLOGIE_GRPC_TARGET", "localhost:50053")
    )
    if not check_health(
        os.getenv(variable, fallback),
        timeout=float(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "2")),
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
