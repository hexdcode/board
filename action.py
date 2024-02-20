import asyncio
from pyppeteer import launch

async def get_page_content(url):
    # 启动浏览器
    browser = await launch(headless=True)  # 确保在无头模式下运行
    page = await browser.newPage()
    # 打开网页
    await page.goto(url)
    # 获取页面内容
    content = await page.content()
    # 打印页面内容
    print(content)
    # 关闭浏览器
    await browser.close()

# 示例URL
url = 'http://example.com'

# 运行异步任务
asyncio.get_event_loop().run_until_complete(get_page_content(url))
