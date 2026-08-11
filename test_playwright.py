from playwright.sync_api import sync_playwright

def test_run():
    # 使用 sync_playwright 启动上下文
    with sync_playwright() as p:
        print("正在启动 Chromium 浏览器...")
        # headless=True 表示无头模式（不弹出浏览器窗口）
        browser = p.chromium.launch(headless=True)
        
        print("正在打开新页面...")
        page = browser.new_page()
        
        print("正在访问百度...")
        page.goto("https://baidu.com")
        
        # 获取网页标题
        title = page.title()
        print(f"网页标题为: {title}")
        
        # 截图保存为 example.png
        page.screenshot(path="example.png")
        print("截图已成功保存为 example.png")
        
        browser.close()
        print("Playwright 环境测试完全正常！")

if __name__ == "__main__":
    test_run()

