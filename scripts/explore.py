import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("ELTAKO_HOST", "192.0.2.1")
port = os.getenv("ELTAKO_PORT", "443")
base = f"https://{host}:{port}"
paths = [
    "",
    "/",
    "/api",
    "/api/",
    "/api/v1",
    "/api/v1/",
    "/api/v2",
    "/swagger",
    "/swagger/",
    "/swagger/index.html",
    "/swagger-ui",
    "/swagger-ui/",
    "/swagger-ui.html",
    "/swagger-ui/index.html",
    "/docs",
    "/docs/",
    "/redoc",
    "/api-docs",
    "/v3/api-docs",
    "/v2/api-docs",
    "/openapi.json",
    "/openapi.yaml",
    "/openapi.yml",
    "/openapi",
    "/swagger.json",
    "/swagger.yaml",
    "/api/swagger",
    "/api/swagger.json",
    "/api/openapi.json",
    "/api/docs",
    "/api/v1/swagger",
    "/api/v1/swagger.json",
    "/api/v1/openapi.json",
    "/api/v1/docs",
    "/api/v1/openapi",
    "/api-spec",
    "/spec",
    "/index.html",
    "/info",
    "/api/info",
]


async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=3.0)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for p in paths:
            url = f"{base}{p}"
            try:
                async with session.get(url, allow_redirects=False) as resp:
                    ct = resp.headers.get("content-type", "")
                    loc = resp.headers.get("location", "")
                    loc_str = f" -> {loc}" if loc else ""
                    print(f"[{resp.status}] {url} ({ct}){loc_str}")
            except Exception as e:
                print(f"[ERR] {url} -> {e}")


if __name__ == "__main__":
    asyncio.run(main())
