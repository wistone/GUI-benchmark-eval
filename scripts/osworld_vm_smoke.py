#!/usr/bin/env python3
"""Run a minimal OSWorld VM smoke test.

This verifies the local virtualization path, VM server, screenshot endpoint,
GUI action execution, and evaluator plumbing.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


TASK = {
    "id": "local-osworld-smoke",
    "instruction": "Local smoke test: verify screenshot, action, and evaluator.",
    "config": [],
    "evaluator": {
        "func": "check_include_exclude",
        "result": {
            "type": "vm_command_line",
            "command": ["bash", "-lc", "printf osworld-smoke-ok"],
        },
        "expected": {
            "type": "rule",
            "rules": {
                "include": ["osworld-smoke-ok"],
                "exclude": ["Traceback", "not found", "error"],
            },
        },
    },
}


def ensure_vmrun_on_path() -> None:
    fusion_vmrun = Path("/Applications/VMware Fusion.app/Contents/Library/vmrun")
    if shutil.which("vmrun"):
        return
    if fusion_vmrun.exists():
        os.environ["PATH"] = f"{fusion_vmrun.parent}{os.pathsep}{os.environ['PATH']}"
        return

    raise RuntimeError(
        "vmrun was not found. Install VMware Fusion first, then rerun this script."
    )


def verify_vmrun() -> None:
    result = subprocess.run(
        ["vmrun", "-T", "fusion", "list"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "vmrun is present but not usable with VMware Fusion:\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--osworld-dir",
        default="external/OSWorld",
        help="Local OSWorld repository directory.",
    )
    parser.add_argument("--provider-name", default="vmware")
    parser.add_argument("--path-to-vm", default=None)
    parser.add_argument("--os-type", default="Ubuntu")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--screenshot-out",
        default="results/osworld_smoke/screenshot.png",
        help="Where to save the screenshot returned by OSWorld.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    original_cwd = Path.cwd()
    osworld_dir = Path(args.osworld_dir)
    if not osworld_dir.is_absolute():
        osworld_dir = original_cwd / osworld_dir
    if not osworld_dir.exists():
        raise RuntimeError(f"OSWorld directory does not exist: {osworld_dir}")

    screenshot_out = Path(args.screenshot_out)
    if not screenshot_out.is_absolute():
        screenshot_out = original_cwd / screenshot_out
    path_to_vm = args.path_to_vm
    if path_to_vm:
        path_to_vm = Path(path_to_vm)
        if not path_to_vm.is_absolute():
            path_to_vm = original_cwd / path_to_vm
        path_to_vm = str(path_to_vm)

    ensure_vmrun_on_path()
    verify_vmrun()

    os.chdir(osworld_dir)
    from desktop_env.desktop_env import DesktopEnv

    env = DesktopEnv(
        provider_name=args.provider_name,
        path_to_vm=path_to_vm,
        os_type=args.os_type,
        action_space="pyautogui",
        headless=args.headless,
        require_a11y_tree=False,
    )
    env.is_environment_used = False

    try:
        observation = env.reset(task_config=TASK)
        screenshot = observation.get("screenshot")
        if not screenshot:
            raise RuntimeError("OSWorld reset completed, but screenshot is empty.")

        screenshot_out.parent.mkdir(parents=True, exist_ok=True)
        screenshot_out.write_bytes(screenshot)

        env.step("pyautogui.moveTo(100, 100); pyautogui.click()")
        score = env.evaluate()
        print(f"screenshot={screenshot_out}")
        print(f"evaluator_score={score}")
        return 0 if float(score) == 1.0 else 2
    finally:
        env.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"smoke_test_failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
