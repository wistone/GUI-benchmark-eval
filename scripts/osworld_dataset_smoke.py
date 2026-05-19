#!/usr/bin/env python3
"""Run a stratified OSWorld dataset smoke test.

This does not try to solve tasks. It verifies that real OSWorld task JSONs
can reset/setup the VM, return an observation, execute a benign GUI action,
and run each task's evaluator without crashing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_TASKS = {
    "chrome": "bb5e4c0d-f964-439c-97b6-bdb9747de3f4",
    "gimp": "7767eef2-56a3-4cea-8c9f-48c070c7d65b",
    "libreoffice_calc": "01b269ae-2111-4a07-81fd-3fcd711993b0",
    "libreoffice_impress": "2cd43775-7085-45d8-89fa-9e35c0a915cf",
    "libreoffice_writer": "0e47de2a-32e0-456c-a366-8c607ef7a9d2",
    "multi_apps": "937087b6-f668-4ba6-9110-60682ee33441",
    "os": "28cc3b7e-b194-4bc9-8353-d04c0f4d56d2",
    "thunderbird": "a10b69e1-6034-4a2b-93e1-571d45194f75",
    "vlc": "215dfd39-f493-4bc3-a027-8a97d72c61bf",
    "vs_code": "57242fad-77ca-454f-b71b-f187181a9f23",
}


def ensure_vmrun_on_path() -> None:
    fusion_vmrun = Path("/Applications/VMware Fusion.app/Contents/Library/vmrun")
    if shutil.which("vmrun"):
        return
    if fusion_vmrun.exists():
        os.environ["PATH"] = f"{fusion_vmrun.parent}{os.pathsep}{os.environ['PATH']}"
        return
    raise RuntimeError("vmrun was not found. Install VMware Fusion first.")


def run_vmrun(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["vmrun", "-T", "fusion", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_snapshot(path_to_vm: str, snapshot_name: str) -> None:
    snapshots = run_vmrun("listSnapshots", path_to_vm)
    if snapshots.returncode == 0 and snapshot_name in snapshots.stdout.splitlines():
        return
    raise RuntimeError(
        f"VM snapshot '{snapshot_name}' is missing. Create it before dataset smoke."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--osworld-dir", default="external/OSWorld")
    parser.add_argument(
        "--path-to-vm",
        default="external/OSWorld/vmware_vm_data/Ubuntu0/Ubuntu0.vmx",
    )
    parser.add_argument("--provider-name", default="vmware")
    parser.add_argument("--os-type", default="Ubuntu")
    parser.add_argument("--snapshot-name", default="init_state")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--domains",
        default=",".join(DEFAULT_TASKS),
        help="Comma-separated OSWorld domains to smoke test.",
    )
    parser.add_argument(
        "--result-dir",
        default="results/osworld_dataset_smoke",
        help="Where to save screenshots and summary JSON.",
    )
    return parser.parse_args()


def load_task(osworld_dir: Path, domain: str, task_id: str) -> dict:
    task_path = osworld_dir / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
    with task_path.open("r", encoding="utf-8") as task_file:
        return json.load(task_file)


def main() -> int:
    args = parse_args()
    original_cwd = Path.cwd()
    osworld_dir = Path(args.osworld_dir)
    if not osworld_dir.is_absolute():
        osworld_dir = original_cwd / osworld_dir
    path_to_vm = Path(args.path_to_vm)
    if not path_to_vm.is_absolute():
        path_to_vm = original_cwd / path_to_vm
    result_dir = Path(args.result_dir)
    if not result_dir.is_absolute():
        result_dir = original_cwd / result_dir

    domains = [domain.strip() for domain in args.domains.split(",") if domain.strip()]
    unknown = [domain for domain in domains if domain not in DEFAULT_TASKS]
    if unknown:
        raise RuntimeError(f"Unknown smoke domains: {unknown}")

    ensure_vmrun_on_path()
    ensure_snapshot(str(path_to_vm), args.snapshot_name)

    os.chdir(osworld_dir)
    from desktop_env.desktop_env import DesktopEnv

    env = DesktopEnv(
        provider_name=args.provider_name,
        path_to_vm=str(path_to_vm),
        snapshot_name=args.snapshot_name,
        os_type=args.os_type,
        action_space="pyautogui",
        headless=args.headless,
        require_a11y_tree=True,
    )

    results = []
    result_dir.mkdir(parents=True, exist_ok=True)
    try:
        for domain in domains:
            task_id = DEFAULT_TASKS[domain]
            task = load_task(osworld_dir, domain, task_id)
            task_result_dir = result_dir / domain / task_id
            task_result_dir.mkdir(parents=True, exist_ok=True)
            started_at = time.time()
            row = {
                "domain": domain,
                "task_id": task_id,
                "instruction": task.get("instruction", ""),
                "status": "error",
                "score": None,
                "screenshot": None,
                "error": None,
                "elapsed_seconds": None,
            }
            print(f"dataset_smoke_start domain={domain} task={task_id}", flush=True)
            try:
                observation = env.reset(task_config=task)
                screenshot = observation.get("screenshot")
                if not screenshot:
                    raise RuntimeError("empty screenshot after reset")
                screenshot_path = task_result_dir / "initial_state.png"
                screenshot_path.write_bytes(screenshot)
                env.step("pyautogui.moveTo(100, 100); pyautogui.click()", pause=0.5)
                score = env.evaluate()
                row["status"] = "ok"
                row["score"] = float(score)
                row["screenshot"] = str(screenshot_path)
                print(
                    f"dataset_smoke_ok domain={domain} task={task_id} score={score}",
                    flush=True,
                )
            except Exception as exc:
                row["error"] = repr(exc)
                print(
                    f"dataset_smoke_error domain={domain} task={task_id} error={exc!r}",
                    flush=True,
                )
            finally:
                row["elapsed_seconds"] = round(time.time() - started_at, 2)
                results.append(row)
                (result_dir / "summary.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
    finally:
        env.close()

    ok_count = sum(row["status"] == "ok" for row in results)
    print(f"dataset_smoke_summary ok={ok_count} total={len(results)}")
    print(f"summary={result_dir / 'summary.json'}")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"dataset_smoke_failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
