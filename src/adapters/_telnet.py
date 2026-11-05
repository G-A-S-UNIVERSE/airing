"""Reusable async Telnet session for OLT adapters.

Both ZTE C320 and C-Data OLTs are driven over Telnet (the CLI), not
SNMP. This helper wraps the common dance: connect, wait for the login
prompt, send credentials, then repeatedly run commands and read output
until a known prompt-marker reappears.

Design notes:
  - Prompts are passed in per-vendor (ZTE: "ZXAN>", "ZXAN#"; C-Data:
    "epon#", "epon>"). The helper never assumes a specific one.
  - Paging ("--More--" / "Press any key to continue") is auto-handled:
    the caller sets `paging_char` (space or newline) and the helper
    sends it whenever a paging marker appears in the stream.
  - Timeouts are explicit and small. A dead OLT fails fast, not after
    a minute.
  - This is not a full terminal emulator. It assumes line-oriented
    output with a stable prompt. If a vendor does something exotic
    (e.g., ANSI escapes mid-prompt), adapt the marker list.

No credentials are stored here. The adapter supplies them from config.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, Sequence

# Default paging markers across vendors we know about.
DEFAULT_PAGING_MARKERS: tuple[str, ...] = (
    "--More--",
    "Press any key to continue",
    "(Q to quit)",
)


class TelnetSession:
    """Minimal line-oriented Telnet client for OLT CLI automation."""

    def __init__(
        self,
        host: str,
        port: int = 23,
        *,
        timeout: float = 5.0,
        paging_char: str = " ",
        paging_markers: Sequence[str] = DEFAULT_PAGING_MARKERS,
        encoding: str = "utf-8",
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.paging_char = paging_char
        self.paging_markers = tuple(paging_markers)
        self.encoding = encoding
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def __aenter__(self) -> "TelnetSession":
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ---- lifecycle -------------------------------------------------

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(
            self.host, self.port
        )

    async def close(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            finally:
                self._writer = None
                self._reader = None

    # ---- low-level I/O ---------------------------------------------

    async def read_until(
        self,
        markers: Iterable[str],
        *,
        timeout: float | None = None,
        max_bytes: int = 1_000_000,
    ) -> str:
        """Read from the socket until any marker appears or we hit limits.

        Returns everything read (including the marker). Raises
        asyncio.TimeoutError on idle socket.
        """
        assert self._reader is not None, "not connected"
        markers = tuple(markers)
        deadline = asyncio.get_event_loop().time() + (timeout or self.timeout)
        buf = bytearray()

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"read_until({markers!r}) timed out after {timeout or self.timeout}s"
                )
            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096), timeout=remaining
                )
            except asyncio.TimeoutError:
                raise
            if not chunk:
                break
            buf.extend(chunk)

            text = buf.decode(self.encoding, errors="ignore")

            # Auto-advance pagers before checking markers, because paging
            # markers themselves are inside the output stream.
            if any(pm in text for pm in self.paging_markers):
                self._writer.write(self.paging_char.encode())
                await self._writer.drain()

            if any(m in text for m in markers):
                return text

            if len(buf) > max_bytes:
                # Safety valve: never buffer unbounded output.
                return text

        return buf.decode(self.encoding, errors="ignore")

    async def send_line(self, line: str) -> None:
        assert self._writer is not None, "not connected"
        self._writer.write((line + "\n").encode(self.encoding))
        await self._writer.drain()

    async def login(
        self,
        username: str,
        password: str,
        *,
        username_prompt_markers: Iterable[str],
        password_prompt_markers: Iterable[str],
        post_login_markers: Iterable[str],
    ) -> None:
        """Drive a typical username/password login flow."""
        await self.read_until(username_prompt_markers, timeout=self.timeout)
        await self.send_line(username)

        await self.read_until(password_prompt_markers, timeout=self.timeout)
        await self.send_line(password)

        # Some OLTs print a warning banner; the post-login prompt is
        # what we ultimately wait for. Drain until any such marker.
        await self.read_until(post_login_markers, timeout=self.timeout)

    async def run(
        self,
        command: str,
        *,
        prompt_markers: Iterable[str],
        timeout: float | None = None,
    ) -> str:
        """Send one command; read its output until the prompt returns."""
        await self.send_line(command)
        return await self.read_until(prompt_markers, timeout=timeout)
