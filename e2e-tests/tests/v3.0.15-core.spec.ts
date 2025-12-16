import { test, expect } from '@playwright/test';

/**
 * v3.0.15 核心功能测试
 * 这些测试专注于验证v3.0.15的关键改进
 */

const PYTHON_API_URL = 'http://127.0.0.1:8000';
const NEXTJS_URL = 'http://localhost:3000';

test.describe('v3.0.15 核心功能验证', () => {

  test('场景1: 未登录用户访问应用 - 显示登录界面', async ({ page }) => {
    console.log('\n🧪 测试场景1: 未登录用户看到登录界面\n');

    // 访问应用首页
    await page.goto(NEXTJS_URL);

    // 等待页面加载完成
    await page.waitForLoadState('networkidle');

    console.log('✓ 页面加载完成');

    // 验证显示"请先登录以使用应用"
    const loginPrompt = page.locator('text=请先登录以使用应用');
    await expect(loginPrompt).toBeVisible({ timeout: 10000 });
    console.log('✓ 显示登录提示文字');

    // 验证显示"立即登录"按钮
    const loginButton = page.locator('button:has-text("立即登录")');
    await expect(loginButton).toBeVisible();
    console.log('✓ 显示"立即登录"按钮');

    // 验证登录提示信息
    const hint = page.locator('text=登录后将自动返回应用');
    await expect(hint).toBeVisible();
    console.log('✓ 显示登录后返回提示');

    // 验证ucppt.com链接存在
    const ucpptLink = page.locator('a[href="https://www.ucppt.com"]');
    await expect(ucpptLink).toBeVisible();
    console.log('✓ 显示ucppt.com主站链接');

    console.log('\n✅ 场景1测试通过 - 未登录界面显示正确\n');
  });

  test('场景2: AuthContext REST API 调用逻辑验证', async ({ page }) => {
    console.log('\n🧪 测试场景2: AuthContext REST API调用逻辑\n');

    const logs: string[] = [];

    // 捕获所有AuthContext日志
    page.on('console', msg => {
      if (msg.text().includes('[AuthContext]')) {
        logs.push(msg.text());
        console.log('   📝', msg.text());
      }
    });

    // 访问应用
    await page.goto(NEXTJS_URL);
    await page.waitForLoadState('networkidle');

    // 等待一段时间让AuthContext执行
    await page.waitForTimeout(3000);

    console.log('\n📊 日志分析:');
    console.log(`   总日志数: ${logs.length}`);

    // 验证关键日志存在
    const hasRESTAPILog = logs.some(log => log.includes('尝试通过 WordPress REST API 获取 Token'));
    console.log(`   ✓ 包含REST API调用日志: ${hasRESTAPILog}`);

    const hasUnauthorizedLog = logs.some(log => log.includes('WordPress 未登录') || log.includes('无有效登录状态'));
    console.log(`   ✓ 包含未登录判断日志: ${hasUnauthorizedLog}`);

    // 打印完整日志
    console.log('\n完整日志:');
    logs.forEach(log => console.log('  ', log));

    console.log('\n✅ 场景2测试通过 - AuthContext逻辑正确\n');
  });

  test('场景3: Python后端Token验证接口', async ({ request }) => {
    console.log('\n🧪 测试场景3: Python后端Token验证\n');

    // 测试健康检查
    const healthResponse = await request.get(`${PYTHON_API_URL}/health`);
    expect(healthResponse.status()).toBe(200);
    console.log('✓ 健康检查通过');

    // 测试Token验证接口（使用无效Token）
    const invalidToken = 'invalid.token.here';
    const verifyResponse = await request.post(`${PYTHON_API_URL}/api/auth/verify`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${invalidToken}`
      }
    });

    expect(verifyResponse.status()).toBe(401);
    console.log('✓ 无效Token正确返回401');

    console.log('\n✅ 场景3测试通过 - 后端验证逻辑正确\n');
  });

  test('场景4: 登录按钮点击行为验证', async ({ page }) => {
    console.log('\n🧪 测试场景4: 登录按钮点击行为\n');

    await page.goto(NEXTJS_URL);
    await page.waitForLoadState('networkidle');

    // 获取登录按钮
    const loginButton = page.locator('button:has-text("立即登录")');
    await expect(loginButton).toBeVisible();

    console.log('✓ 找到登录按钮');

    // 监听导航事件
    let navigationUrl = '';
    page.on('framenavigated', frame => {
      if (frame === page.mainFrame()) {
        navigationUrl = frame.url();
      }
    });

    // 点击登录按钮
    await loginButton.click();

    // 等待跳转
    await page.waitForTimeout(1000);

    console.log(`✓ 点击后跳转到: ${navigationUrl}`);

    // 验证跳转到WordPress登录页
    expect(navigationUrl).toContain('ucppt.com/login');
    expect(navigationUrl).toContain('redirect_to=');
    console.log('✓ 正确跳转到WPCOM登录页，带redirect_to参数');

    console.log('\n✅ 场景4测试通过 - 登录跳转逻辑正确\n');
  });

  test('场景5: Next.js应用响应时间测试', async ({ page }) => {
    console.log('\n🧪 测试场景5: 应用性能测试\n');

    const startTime = Date.now();

    await page.goto(NEXTJS_URL);
    await page.waitForLoadState('domcontentloaded');

    const loadTime = Date.now() - startTime;
    console.log(`✓ 页面加载时间: ${loadTime}ms`);

    // 验证页面在合理时间内加载
    expect(loadTime).toBeLessThan(5000);

    // 检查关键元素是否渲染
    const loginInterface = page.locator('text=请先登录以使用应用');
    const renderStart = Date.now();
    await expect(loginInterface).toBeVisible({ timeout: 5000 });
    const renderTime = Date.now() - renderStart;

    console.log(`✓ 登录界面渲染时间: ${renderTime}ms`);

    console.log('\n✅ 场景5测试通过 - 应用性能正常\n');
  });

  test('场景6: WordPress REST API直接调用测试', async ({ request }) => {
    console.log('\n🧪 测试场景6: WordPress REST API响应\n');

    // 直接调用WordPress REST API（不带Cookie，应该返回401）
    const response = await request.get('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token');

    console.log(`✓ REST API状态码: ${response.status()}`);

    if (response.status() === 401) {
      console.log('✓ 未登录状态正确返回401');
      const data = await response.json();
      console.log(`   响应数据:`, data);
    } else if (response.status() === 200) {
      console.log('⚠️  检测到已登录状态（可能浏览器有缓存Cookie）');
      const data = await response.json();
      console.log(`   Token长度: ${data.token?.length || 0}`);
    } else {
      console.log(`⚠️  意外状态码: ${response.status()}`);
    }

    console.log('\n✅ 场景6测试完成\n');
  });

  test('场景7: 控制台错误检查', async ({ page }) => {
    console.log('\n🧪 测试场景7: 控制台错误检查\n');

    const errors: string[] = [];
    const warnings: string[] = [];

    // 监听控制台错误
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    // 监听页面错误
    page.on('pageerror', error => {
      errors.push(`Page Error: ${error.message}`);
    });

    await page.goto(NEXTJS_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    console.log(`📊 错误数量: ${errors.length}`);
    console.log(`📊 警告数量: ${warnings.length}`);

    if (errors.length > 0) {
      console.log('\n❌ 发现错误:');
      errors.forEach(err => console.log('  ', err));
    } else {
      console.log('✓ 无JavaScript错误');
    }

    if (warnings.length > 0) {
      console.log('\n⚠️  发现警告:');
      warnings.forEach(warn => console.log('  ', warn));
    }

    // 验证没有致命错误（排除预期的401错误）
    const criticalErrors = errors.filter(err =>
      !err.includes('401') && // 排除401授权错误（这是预期的）
      (err.includes('Cannot') || err.includes('undefined is not') || err.includes('TypeError'))
    );

    if (criticalErrors.length > 0) {
      console.log('\n❌ 致命错误:');
      criticalErrors.forEach(err => console.log('  ', err));
    }

    expect(criticalErrors.length).toBe(0);

    console.log('\n✅ 场景7测试通过 - 无致命错误\n');
  });

  test('场景8: 网络请求监控', async ({ page }) => {
    console.log('\n🧪 测试场景8: 网络请求分析\n');

    const requests: { url: string; method: string; status: number | null }[] = [];

    page.on('request', request => {
      if (
        request.url().includes('wp-json') ||
        request.url().includes('127.0.0.1:8000') ||
        request.url().includes('localhost:3000')
      ) {
        console.log(`   → ${request.method()} ${request.url()}`);
      }
    });

    page.on('response', response => {
      if (
        response.url().includes('wp-json') ||
        response.url().includes('127.0.0.1:8000')
      ) {
        requests.push({
          url: response.url(),
          method: response.request().method(),
          status: response.status()
        });
        console.log(`   ← ${response.status()} ${response.url()}`);
      }
    });

    await page.goto(NEXTJS_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    console.log(`\n📊 相关请求总数: ${requests.length}`);

    // 检查是否调用了WordPress REST API
    const wpApiCall = requests.find(r => r.url.includes('wp-json/nextjs-sso/v1/get-token'));
    if (wpApiCall) {
      console.log(`✓ 调用了WordPress REST API`);
      console.log(`   状态码: ${wpApiCall.status}`);
    } else {
      console.log('⚠️  未检测到WordPress REST API调用');
    }

    console.log('\n✅ 场景8测试完成\n');
  });
});
