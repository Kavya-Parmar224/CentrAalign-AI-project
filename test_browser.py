import asyncio
from agent.tools.browser_tool import BrowserTool

async def test():
    bt = BrowserTool()
    print("starting browser")
    res = await bt.execute('navigate', url='http://localhost:5001')
    print("result:", res)
    await bt.close()

if __name__ == '__main__':
    asyncio.run(test())
