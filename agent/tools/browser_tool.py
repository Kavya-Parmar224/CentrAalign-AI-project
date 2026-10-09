import asyncio, os, logging, base64
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, Playwright
from agent.schemas import ToolResult

logger = logging.getLogger(__name__)
SCREENSHOT_DIR = os.environ.get('SCREENSHOT_DIR', './screenshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class BrowserTool:
    def __init__(self):
        self._playwright: Playwright = None
        self._browser: Browser = None
        self._page: Page = None
    
    async def ensure_started(self):
        if self._page is None:
            try:
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                if self._browser is None:
                    self._browser = await self._playwright.chromium.launch(headless=False)
                self._page = await self._browser.new_page()
                self._page.set_default_timeout(10000)
                logger.info('Browser started')
            except Exception as e:
                # Reset state so retries don't think it's partially started
                self._page = None
                self._browser = None
                if self._playwright:
                    await self._playwright.stop()
                    self._playwright = None
                raise e
    
    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def _screenshot(self, label: str = '') -> str:
        fname = f'{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}_{label}.png'
        path = os.path.join(SCREENSHOT_DIR, fname)
        await self._page.screenshot(path=path, full_page=False)
        return path
    
    async def execute(self, action: str, url: str = None, selector: str = None,
                      text: str = None, value: str = None, timeout: int = 10000) -> ToolResult:
        await self.ensure_started()
        try:
            shot = None
            if action == 'navigate':
                await self._page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                shot = await self._screenshot('navigate')
                title = await self._page.title()
                return ToolResult(success=True, output={'title': title, 'url': self._page.url}, screenshot_path=shot)
            
            elif action == 'click':
                if selector:
                    await self._page.click(selector, timeout=timeout)
                else:
                    await self._page.get_by_text(text, exact=False).first.click(timeout=timeout)
                shot = await self._screenshot('click')
                return ToolResult(success=True, output='Clicked successfully', screenshot_path=shot)
            
            elif action == 'fill':
                await self._page.fill(selector, value, timeout=timeout)
                shot = await self._screenshot('fill')
                return ToolResult(success=True, output=f'Filled {selector} with value', screenshot_path=shot)
            
            elif action == 'select':
                if value:
                    await self._page.select_option(selector, value=value, timeout=timeout)
                elif text:
                    await self._page.select_option(selector, label=text, timeout=timeout)
                shot = await self._screenshot('select')
                return ToolResult(success=True, output=f'Selected option in {selector}', screenshot_path=shot)
            
            elif action == 'extract_text':
                if selector:
                    elem = self._page.locator(selector)
                    content = await elem.inner_text(timeout=timeout)
                else:
                    content = await self._page.inner_text('body')
                return ToolResult(success=True, output=content[:5000])
            
            elif action == 'screenshot':
                shot = await self._screenshot('manual')
                return ToolResult(success=True, output=shot, screenshot_path=shot)
            
            elif action == 'get_page_source':
                html = await self._page.content()
                return ToolResult(success=True, output=html[:8000])
            
            elif action == 'find_elements':
                elements = await self._page.query_selector_all(selector)
                results = []
                for el in elements[:20]:
                    txt = await el.inner_text()
                    results.append(txt.strip())
                return ToolResult(success=True, output=results)
            
            elif action == 'wait':
                await self._page.wait_for_selector(selector, timeout=timeout)
                return ToolResult(success=True, output='Element found')
            
            elif action == 'submit_form':
                await self._page.keyboard.press('Enter')
                await asyncio.sleep(1)
                shot = await self._screenshot('submit')
                return ToolResult(success=True, output='Form submitted', screenshot_path=shot)
            
            elif action == 'scroll':
                await self._page.evaluate('window.scrollBy(0, 500)')
                return ToolResult(success=True, output='Scrolled')
            
            elif action == 'get_current_url':
                return ToolResult(success=True, output=self._page.url)
            
            else:
                return ToolResult(success=False, error=f'Unknown action: {action}')
        except Exception as e:
            logger.error(f'Browser action {action} failed: {e}')
            try:
                shot = await self._screenshot('error')
            except:
                shot = None
            return ToolResult(success=False, error=str(e), screenshot_path=shot)


def create_browser_tool(browser: BrowserTool) -> dict:
    """Returns Tool kwargs for registration."""
    async def browser_execute(action: str, url: str = None, selector: str = None,
                               text: str = None, value: str = None, timeout: int = 10000):
        return await browser.execute(action=action, url=url, selector=selector,
                                      text=text, value=value, timeout=timeout)
    return {
        'name': 'browser',
        'description': (
            'Control a real web browser. Use to navigate websites, click elements, fill forms, '
            'select dropdowns, extract text, and take screenshots. The browser is visible (not headless).'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['navigate', 'click', 'fill', 'select', 'extract_text', 'screenshot',
                             'get_page_source', 'find_elements', 'wait', 'submit_form',
                             'scroll', 'get_current_url'],
                    'description': 'The browser action to perform'
                },
                'url': {'type': 'string', 'description': 'URL for navigate action'},
                'selector': {'type': 'string', 'description': 'CSS selector for element targeting'},
                'text': {'type': 'string', 'description': 'Text content to find element by, or Label for select action'},
                'value': {'type': 'string', 'description': 'Value to fill into input field, or Value for select action'},
                'timeout': {'type': 'integer', 'description': 'Timeout in ms (default 10000)', 'default': 10000}
            },
            'required': ['action']
        },
        'fn': browser_execute
    }
