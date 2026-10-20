"""Configuration optionnelle TLS/mTLS des serveurs gRPC."""
import os
from pathlib import Path

import grpc


def server_credentials_from_env():
    cert_path = os.getenv("GRPC_TLS_CERT")
    key_path = os.getenv("GRPC_TLS_KEY")
    client_ca_path = os.getenv("GRPC_TLS_CLIENT_CA")
    if not cert_path and not key_path and not client_ca_path:
        return None
    if not cert_path or not key_path:
        raise ValueError("GRPC_TLS_CERT et GRPC_TLS_KEY doivent être fournis ensemble.")
    cert = Path(cert_path).read_bytes()
    key = Path(key_path).read_bytes()
    client_ca = Path(client_ca_path).read_bytes() if client_ca_path else None
    return grpc.ssl_server_credentials(
        ((key, cert),),
        root_certificates=client_ca,
        require_client_auth=client_ca is not None,
    )
