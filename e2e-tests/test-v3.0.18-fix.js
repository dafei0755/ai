// 测试 v3.0.18 WPCOM登录修复
// 验证登录URL是否包含 login_type=password 参数

const { chromium } = require('@playwright/test');

(async () => {
  console.log('🚀 开始测试 WPCOM登录修复 v3.0.18...\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 记录网络请求
  const requests = [];
  page.on('request', request => {
    const url = request.url();
    if (url.includes('ucppt.com/login') || url.includes('wp-json')) {
      requests.push({
        method: request.method(),
        url: url
      });
    }
  });

  try {
    console.log('✓ 步骤1: 访问 localhost:3000');
    await page.goto('http://localhost:3000', { timeout: 15000 });
    await page.waitForTimeout(2000);

    console.log('✓ 步骤2: 检查是否显示登录界面');
    const loginButton = await page.locator('button:has-text("立即登录")');
    const isVisible = await loginButton.isVisible();

    if (!isVisible) {
      console.log('❌ 未找到"立即登录"按钮');
      await browser.close();
      return;
    }
    console.log('✓ "立即登录"按钮可见');

    console.log('\n✓ 步骤3: 模拟点击登录按钮');

    // 监听导航事件
    const navigationPromise = page.waitForURL(/ucppt\.com\/login/, { timeout: 10000 });

    await loginButton.click();

    // 等待跳转
    await navigationPromise;

    const currentUrl = page.url();
    console.log(`\n✓ 步骤4: 已跳转到登录页面`);
    console.log(`   当前URL: ${currentUrl}`);

    // 验证关键参数
    console.log('\n🔍 验证修复是否生效:');

    const hasLoginType = currentUrl.includes('login_type=password');
    const hasRedirectTo = currentUrl.includes('redirect_to=');

    console.log(`   ✓ 包含 login_type=password: ${hasLoginType ? '✅ 是' : '❌ 否'}`);
    console.log(`   ✓ 包含 redirect_to: ${hasRedirectTo ? '✅ 是' : '❌ 否'}`);

    // 检查是否有400错误
    await page.waitForTimeout(3000);

    console.log('\n📊 网络请求分析:');
    requests.forEach(req => {
      console.log(`   → ${req.method} ${req.url}`);
    });

    const has400 = requests.some(req => req.url.includes('mwp-sign-sign.php'));
    console.log(`\n   问题端点 /mwp-sign-sign.php: ${has400 ? '❌ 仍然存在' : '✅ 已绕过'}`);

    // 测试结果
    console.log('\n' + '='.repeat(60));
    if (hasLoginType && hasRedirectTo && !has400) {
      console.log('✅ 测试通过！v3.0.18修复生效');
      console.log('   - 登录URL正确包含 login_type=password');
      console.log('   - 成功绕过手机快捷登录接口');
      console.log('   - 无400错误');
    } else {
      console.log('❌ 测试失败，需要进一步调试');
      if (!hasLoginType) console.log('   - 缺少 login_type=password 参数');
      if (!hasRedirectTo) console.log('   - 缺少 redirect_to 参数');
      if (has400) console.log('   - 仍然调用了问题端点');
    }
    console.log('='.repeat(60));

  } catch (error) {
    console.log(`\n❌ 测试错误: ${error.message}`);
  } finally {
    await page.waitForTimeout(5000); // 保持浏览器打开5秒
    await browser.close();
    console.log('\n✓ 测试完成');
  }
})();
