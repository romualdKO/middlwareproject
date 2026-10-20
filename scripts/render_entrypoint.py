"""Lance toute la pile dans un web service Docker unique (démo Render)."""
import os
import signal
import subprocess
import sys
import time

from grpc_services.clients import check_health


ROOT_MODULES = (
    ("pharmacie", "PHARMACIE_PORT", "PHARMACIE_GRPC_TARGET", "grpc_services.pharmacie_server"),
    ("radiologie", "RADIOLOGIE_PORT", "RADIOLOGIE_GRPC_TARGET", "grpc_services.radiologie_server"),
)


def _start_grpc_services():
    environment = os.environ.copy()
    environment.setdefault("GRPC_BIND_HOST", "127.0.0.1")
    processes = []
    health_targets = []
    for label, port_key, target_key, module in ROOT_MODULES:
        port = int(environment.get(port_key, "50052" if label == "pharmacie" else "50053"))
        environment[port_key] = str(port)
        target = environment.get(target_key, f"127.0.0.1:{port}")
        environment[target_key] = target
        processes.append((label, subprocess.Popen([sys.executable, "-m", module], env=environment)))
        health_targets.append((label, target))
    return processes, health_targets, environment


def _wait_for_grpc(processes, targets, timeout=45):
    deadline = time.monotonic() + timeout
    pending = dict(targets)
    while pending and time.monotonic() < deadline:
        for label, process in processes:
            if process.poll() is not None:
                raise RuntimeError(f"Le serveur gRPC {label} s'est arrêté (code {process.returncode}).")
        for label, target in list(pending.items()):
            if check_health(target, timeout=1):
                del pending[label]
        if pending:
            time.sleep(0.25)
    if pending:
        raise TimeoutError(f"Délai d'attente des services gRPC dépassé : {', '.join(pending)}.")


def _stop(processes):
    for _, process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
    for _, process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    processes = []
    try:
        processes, targets, environment = _start_grpc_services()
        _wait_for_grpc(processes, targets)
        port = int(environment.get("PORT", "10000"))
        if not 1 <= port <= 65535:
            raise ValueError("PORT doit être compris entre 1 et 65535.")
        print(f"Services gRPC prêts; passerelle HTTP à l'écoute sur 0.0.0.0:{port}.", flush=True)
        import uvicorn
        uvicorn.run("rest_services.gateway:app", host="0.0.0.0", port=port, access_log=True)
    finally:
        _stop(processes)


if __name__ == "__main__":
    main()
