import logger
import json
from discord.ext.ipcx import Client
from fastapi import Response
from typing import Any, Optional


class IPCResponse(Response):
    def __init__(
        self,
        content: Any = None,
        ipc_content: Any = None,
        status_code: int = 200,
        error: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(content=content, status_code=status_code, **kwargs)
        self.ipc_content = ipc_content
        self.error = error
        self.success = error is None


class IPCXC:
    """codygen's wrapper around discord-ext-ipcx's Client"""

    def __init__(self, client: Client) -> None:
        self.client = client

    async def request(self, endpoint: str, **kwargs):
        req = await self.client.request(endpoint, **kwargs)

        error = None
        code = 200
        if isinstance(req, dict):
            error = req.get("error", error)
            code = req.get("code", 500 if error else code)

        if error == "Invalid or no endpoint given.":
            code = 500
            req["code"] = code

        resp = IPCResponse(content=json.dumps(req), status_code=code, ipc_content=req)
        if error:
            resp.error = error
            logger.warning(f"error: {error}")

        return resp
