from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.security import is_path_safe
from app.tools.base import BaseTool, RiskLevel, ToolMeta, ToolResult

logger = structlog.get_logger("tools.terminal")

DENIED_COMMANDS = {
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){", "fork",
    "chmod -R 777 /", "wget", "curl|sh", "shutdown", "reboot",
    "init 0", "init 6", "> /dev/sda",
}

HIGH_RISK_PATTERNS = {"rm ", "rmdir", "kill ", "pkill", "apt ", "pip install", "npm install",
                       "systemctl", "service ", "mount", "umount", "iptables"}


class TerminalTool(BaseTool):
    def __init__(self, allowed_workspaces: list[str] | None = None, timeout: int = 30):
        self._workspaces = allowed_workspaces or []
        self._timeout = timeout

    @property
    def meta(self) -> ToolMeta:
        return ToolMeta(
            name="run_command",
            description="Execute a shell command in an allowed workspace directory. Dangerous commands require confirmation.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "working_dir": {"type": "string", "description": "Working directory"},
                },
                "required": ["command"],
            },
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            tags=["terminal", "system"],
        )

    def _is_denied(self, command: str) -> bool:
        cmd_lower = command.lower().strip()
        return any(d in cmd_lower for d in DENIED_COMMANDS)

    def _is_high_risk(self, command: str) -> bool:
        cmd_lower = command.lower().strip()
        return any(p in cmd_lower for p in HIGH_RISK_PATTERNS)

    async def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs["command"]
        working_dir = kwargs.get("working_dir")

        if self._is_denied(command):
            return ToolResult(success=False, output=None, error="Command is blocked by security policy.")

        if working_dir and not is_path_safe(working_dir, self._workspaces):
            return ToolResult(success=False, output=None, error=f"Working directory not in approved workspaces: {working_dir}")

        if self._is_high_risk(command):
            logger.warning("high_risk_command", command=command)

        try:
            timeout = get_settings().terminal_timeout
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            return ToolResult(
                success=proc.returncode == 0,
                output={
                    "stdout": stdout_str[:10000],
                    "stderr": stderr_str[:5000],
                    "return_code": proc.returncode,
                },
                error=stderr_str[:2000] if proc.returncode != 0 else None,
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error=f"Command timed out after {self._timeout}s")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def confirm_prompt(self, **kwargs: Any) -> str | None:
        command = kwargs.get("command", "")
        if self._is_high_risk(command):
            return f"This command may be destructive: '{command}'. Do you want to proceed?"
        return None
