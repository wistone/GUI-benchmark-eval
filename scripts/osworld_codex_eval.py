#!/usr/bin/env python3
"""Run OSWorld tasks with the local Codex CLI as the agent.

The runner keeps OSWorld's environment/evaluator path intact:
task JSON -> DesktopEnv.reset -> Codex CLI predicts pyautogui -> env.step -> env.evaluate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


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


SYSTEM_GUIDANCE = """You are controlling an Ubuntu desktop VM for OSWorld evaluation.
Return only JSON matching the provided schema.
Do not ask the user questions.
Do not use shell/tools to inspect the host. Decide the next VM GUI action from the screenshot and task state.

The action field must be one of:
- pyautogui Python code, for example: pyautogui.click(100, 200)
- WAIT
- DONE
- FAIL

Use pyautogui only. Keep each action small and executable.
When the task appears completed, return DONE.
When the task is impossible or blocked, return FAIL.
"""


def ensure_executable(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    codex_app_path = "/Applications/Codex.app/Contents/Resources/codex"
    if name == "codex" and Path(codex_app_path).exists():
        return codex_app_path
    raise RuntimeError(f"{name} not found on PATH")


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
    raise RuntimeError(f"VM snapshot '{snapshot_name}' is missing.")


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
    parser.add_argument("--domains", default=",".join(DEFAULT_TASKS))
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--codex-bin", default=None)
    parser.add_argument(
        "--schema",
        default="schemas/codex_osworld_action.schema.json",
    )
    parser.add_argument(
        "--result-dir",
        default="results/osworld_codex_eval",
    )
    return parser.parse_args()


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def load_task(osworld_dir: Path, domain: str, task_id: str) -> dict[str, Any]:
    task_path = osworld_dir / "evaluation_examples" / "examples" / domain / f"{task_id}.json"
    with task_path.open("r", encoding="utf-8") as task_file:
        return json.load(task_file)


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def build_prompt(task: dict[str, Any], step_index: int, history: list[dict[str, Any]]) -> str:
    history_text = json.dumps(history[-5:], ensure_ascii=False, indent=2)
    return f"""{SYSTEM_GUIDANCE}

Task instruction:
{task["instruction"]}

Current step: {step_index}

Recent action history:
{history_text}

Return exactly one next action as JSON.
"""


def call_codex(
    codex_bin: str,
    model: str | None,
    schema_path: Path,
    screenshot_path: Path,
    prompt: str,
    workdir: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="osworld-codex-") as tmpdir:
        response_path = Path(tmpdir) / "response.json"
        command = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "-C",
            str(workdir),
            "-i",
            str(screenshot_path),
        ]
        if model:
            command.extend(["--model", model])
        result = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "codex exec failed: "
                + (result.stderr.strip() or result.stdout.strip() or str(result.returncode))
            )
        return extract_json_object(response_path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    original_cwd = Path.cwd()
    osworld_dir = resolve_path(original_cwd, args.osworld_dir)
    path_to_vm = resolve_path(original_cwd, args.path_to_vm)
    schema_path = resolve_path(original_cwd, args.schema)
    result_dir = resolve_path(original_cwd, args.result_dir)
    domains = [domain.strip() for domain in args.domains.split(",") if domain.strip()]

    unknown = [domain for domain in domains if domain not in DEFAULT_TASKS]
    if unknown:
        raise RuntimeError(f"Unknown domains for this runner: {unknown}")

    codex_bin = args.codex_bin or ensure_executable("codex")
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
        require_a11y_tree=False,
    )

    summary = []
    result_dir.mkdir(parents=True, exist_ok=True)
    try:
        for domain in domains:
            task_id = DEFAULT_TASKS[domain]
            task = load_task(osworld_dir, domain, task_id)
            task_dir = result_dir / domain / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            history: list[dict[str, Any]] = []
            row = {
                "domain": domain,
                "task_id": task_id,
                "status": "error",
                "score": None,
                "error": None,
            }
            print(f"codex_eval_start domain={domain} task={task_id}", flush=True)
            try:
                observation = env.reset(task_config=task)
                for step_index in range(1, args.max_steps + 1):
                    screenshot = observation.get("screenshot")
                    if not screenshot:
                        raise RuntimeError("empty screenshot")
                    screenshot_path = task_dir / f"step_{step_index}.png"
                    screenshot_path.write_bytes(screenshot)
                    response = call_codex(
                        codex_bin=codex_bin,
                        model=args.model,
                        schema_path=schema_path,
                        screenshot_path=screenshot_path,
                        prompt=build_prompt(task, step_index, history),
                        workdir=original_cwd,
                    )
                    action = response["action"].strip()
                    history.append({"step": step_index, **response})
                    with (task_dir / "traj.jsonl").open("a", encoding="utf-8") as traj_file:
                        traj_file.write(json.dumps(history[-1], ensure_ascii=False) + "\n")
                    print(f"codex_eval_action step={step_index} action={action}", flush=True)
                    if action in {"DONE", "FAIL"}:
                        env.step(action, pause=0.5)
                        break
                    observation, _, _, _ = env.step(action, pause=1.0)
                score = env.evaluate()
                row["status"] = "ok"
                row["score"] = float(score)
                (task_dir / "result.txt").write_text(f"{score}\n", encoding="utf-8")
                print(f"codex_eval_ok domain={domain} task={task_id} score={score}", flush=True)
            except Exception as exc:
                row["error"] = repr(exc)
                print(f"codex_eval_error domain={domain} task={task_id} error={exc!r}", flush=True)
            finally:
                summary.append(row)
                (result_dir / "summary.json").write_text(
                    json.dumps(summary, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
    finally:
        env.close()

    ok_count = sum(row["status"] == "ok" for row in summary)
    print(f"codex_eval_summary ok={ok_count} total={len(summary)}")
    print(f"summary={result_dir / 'summary.json'}")
    return 0 if ok_count == len(summary) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"codex_eval_failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
