import { test, expect } from '@playwright/test';

// 配置：WordPress登录凭据（从环境变量读取）
const WORDPRESS_URL = process.env.WORDPRESS_URL || 'https://www.ucppt.com';
const WORDPRESS_USERNAME = process.env.WORDPRESS_USERNAME || '';
const WORDPRESS_PASSWORD = process.env.WORDPRESS_PASSWORD || '';
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

test.describe('WordPress SSO v3.0.15 完整流程测试', () => {

  // 测试1: Python后端健康检查
  test('1. Python后端健康检查', async ({ request }) => {
    console.log('[Test 1] 检查Python后端...');

    const response = await request.get(`${PYTHON_API_URL}/health`);

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.status).toBe('healthy');

    console.log('✅ Python后端运行正常');
  });

  // 测试2: WordPress REST API Token获取（未登录）
  test('2. WordPress REST API - 未登录状态', async ({ request }) => {
    console.log('[Test 2] 测试未登录状态的REST API...');

    // 创建新的上下文，确保没有Cookie
    const response = await request.get(`${WORDPRESS_URL}/wp-json/nextjs-sso/v1/get-token`);

    expect(response.status()).toBe(401);

    console.log('✅ 未登录状态正确返回401');
  });

  // 测试3: WordPress登录
  test('3. WordPress WPCOM登录', async ({ page }) => {
    console.log('[Test 3] 自动登录WordPress...');

    if (!WORDPRESS_USERNAME || !WORDPRESS_PASSWORD) {
      test.skip();
      console.log('⚠️ 未配置登录凭据，跳过登录测试');
      return;
    }

    // 访问登录页面
    await page.goto(`${WORDPRESS_URL}/login`);

    // 填写登录表单（需要根据实际WPCOM登录页面调整选择器）
    await page.fill('input[name="log"]', WORDPRESS_USERNAME);
    await page.fill('input[name="pwd"]', WORDPRESS_PASSWORD);

    // 点击登录按钮
    await page.click('button[type="submit"]');

    // 等待登录完成（检查是否跳转或显示用户名）
    await page.waitForURL(WORDPRESS_URL, { timeout: 10000 });

    console.log('✅ 登录成功');
  });

  // 测试4: WordPress REST API Token获取（已登录）
  test('4. WordPress REST API - 已登录状态', async ({ page, request }) => {
    console.log('[Test 4] 测试已登录状态的REST API...');

    // 先登录（复用Cookie）
    if (WORDPRESS_USERNAME && WORDPRESS_PASSWORD) {
      await page.goto(`${WORDPRESS_URL}/login`);
      await page.fill('input[name="log"]', WORDPRESS_USERNAME);
      await page.fill('input[name="pwd"]', WORDPRESS_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL(WORDPRESS_URL, { timeout: 10000 });
    }

    // 在页面上下文中调用API（会携带Cookie）
    const tokenData = await page.evaluate(async () => {
      const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      return {
        status: response.status,
        data: await response.json()
      };
    });

    expect(tokenData.status).toBe(200);
    expect(tokenData.data.success).toBe(true);
    expect(tokenData.data.token).toBeTruthy();
    expect(tokenData.data.token.length).toBeGreaterThan(100);

    console.log('✅ Token获取成功');
    console.log(`   Token长度: ${tokenData.data.token.length}`);
    console.log(`   用户ID: ${tokenData.data.user.ID}`);
  });

  // 测试5: Next.js应用 - 未登录状态
  test('5. Next.js应用 - 未登录状态显示登录界面', async ({ page }) => {
    console.log('[Test 5] 测试未登录状态的应用界面...');

    // 访问应用（使用无Cookie的新上下文）
    await page.goto('http://localhost:3000');

    // 等待加载完成
    await page.waitForLoadState('networkidle');

    // 验证显示登录界面
    await expect(page.locator('text=请先登录以使用应用')).toBeVisible();
    await expect(page.locator('button:has-text("立即登录")')).toBeVisible();

    console.log('✅ 未登录状态正确显示登录界面');
  });

  // 测试6: Next.js应用 - 已登录状态自动跳转
  test('6. Next.js应用 - 已登录状态自动跳转到分析页面', async ({ page }) => {
    console.log('[Test 6] 测试已登录状态的自动跳转...');

    // 先登录WordPress
    if (WORDPRESS_USERNAME && WORDPRESS_PASSWORD) {
      await page.goto(`${WORDPRESS_URL}/login`);
      await page.fill('input[name="log"]', WORDPRESS_USERNAME);
      await page.fill('input[name="pwd"]', WORDPRESS_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL(WORDPRESS_URL, { timeout: 10000 });
    } else {
      test.skip();
      console.log('⚠️ 未配置登录凭据，跳过此测试');
      return;
    }

    // 监听控制台日志
    const logs: string[] = [];
    page.on('console', msg => {
      if (msg.text().includes('[AuthContext]')) {
        logs.push(msg.text());
        console.log('   📝', msg.text());
      }
    });

    // 访问应用
    await page.goto('http://localhost:3000');

    // 等待自动跳转到 /analysis
    await page.waitForURL('http://localhost:3000/analysis', { timeout: 10000 });

    // 验证控制台日志
    expect(logs.some(log => log.includes('REST API Token 验证成功'))).toBe(true);
    expect(logs.some(log => log.includes('检测到已登录，跳转到分析页面'))).toBe(true);

    console.log('✅ 已登录状态自动跳转成功');
  });

  // 测试7: 完整用户流程 - 宣传页面点击按钮
  test('7. 完整流程 - 从宣传页面到应用', async ({ page, context }) => {
    console.log('[Test 7] 测试完整用户流程...');

    // 先登录WordPress
    if (WORDPRESS_USERNAME && WORDPRESS_PASSWORD) {
      await page.goto(`${WORDPRESS_URL}/login`);
      await page.fill('input[name="log"]', WORDPRESS_USERNAME);
      await page.fill('input[name="pwd"]', WORDPRESS_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL(WORDPRESS_URL, { timeout: 10000 });
    } else {
      test.skip();
      console.log('⚠️ 未配置登录凭据，跳过此测试');
      return;
    }

    // 访问宣传页面
    await page.goto(`${WORDPRESS_URL}/js`);

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 查找"立即使用"按钮（根据实际shortcode渲染的HTML调整）
    const button = page.locator('button:has-text("立即使用")').first();
    await expect(button).toBeVisible();

    // 监听新窗口
    const [newPage] = await Promise.all([
      context.waitForEvent('page'),
      button.click()
    ]);

    // 等待新窗口加载
    await newPage.waitForLoadState('networkidle');

    // 监听新窗口的控制台日志
    const appLogs: string[] = [];
    newPage.on('console', msg => {
      if (msg.text().includes('[AuthContext]')) {
        appLogs.push(msg.text());
        console.log('   📝 新窗口:', msg.text());
      }
    });

    // 等待跳转到 /analysis
    await newPage.waitForURL('http://localhost:3000/analysis', { timeout: 10000 });

    // 验证日志
    expect(appLogs.some(log => log.includes('REST API Token 验证成功'))).toBe(true);

    console.log('✅ 完整流程测试通过');
  });

  // 测试8: Token验证
  test('8. Token验证流程', async ({ page, request }) => {
    console.log('[Test 8] 测试Token验证...');

    // 先登录并获取Token
    if (WORDPRESS_USERNAME && WORDPRESS_PASSWORD) {
      await page.goto(`${WORDPRESS_URL}/login`);
      await page.fill('input[name="log"]', WORDPRESS_USERNAME);
      await page.fill('input[name="pwd"]', WORDPRESS_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL(WORDPRESS_URL, { timeout: 10000 });
    } else {
      test.skip();
      return;
    }

    // 获取Token
    const tokenData = await page.evaluate(async () => {
      const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
        credentials: 'include'
      });
      const data = await response.json();
      return data.token;
    });

    expect(tokenData).toBeTruthy();

    // 验证Token
    const verifyResponse = await request.post(`${PYTHON_API_URL}/api/auth/verify`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${tokenData}`
      }
    });

    expect(verifyResponse.status()).toBe(200);

    const verifyData = await verifyResponse.json();
    expect(verifyData.user).toBeTruthy();
    expect(verifyData.user.username).toBeTruthy();

    console.log('✅ Token验证成功');
    console.log(`   验证用户: ${verifyData.user.username}`);
  });
});
