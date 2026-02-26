import sys
import asyncio
import uvicorn

# Force Windows Proactor Loop for Playwright compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    # Disable reload to prevent loop conflicts on Windows spawn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)
