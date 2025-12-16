// 测试 v3.0.20 跨域Cookie修复（URL Token传递）
// 验证用户在 ucppt.com 登录后，点击应用链接能自动登录到 localhost:3000

const { chromium } = require('@playwright/test');

(async () => {
  console.log('🚀 开始测试跨域Cookie修复 v3.0.20...\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 记录网络请求
  const requests = [];
  const errors = [];

  page.on('request', request => {
    const url = request.url();
    if (url.includes('ucppt.com') || url.includes('localhost:3000')) {
      requests.push({
        method: request.method(),
        url: url,
        timestamp: new Date().toISOString()
      });
    }
  });

  page.on('response', response => {
    const url = response.url();
    if (response.status() === 401 || response.status() === 400) {
      errors.push({
        status: response.status(),
        url: url,
        timestamp: new Date().toISOString()
      });
    }
  });

  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('❌') || text.includes('错误') || text.includes('Error')) {
      console.log(`   [浏览器控制台] ${text}`);
    }
  });

  try {
    console.log('='.repeat(70));
    console.log('📋 测试场景：跨域Cookie + URL Token传递');
    console.log('='.repeat(70));

    // ==================== 步骤1：访问宣传页面 ====================
    console.log('\n✓ 步骤1: 访问 ucppt.com/js（宣传页面）');
    await page.goto('https://www.ucppt.com/js', {
      timeout: 20000,
      waitUntil: 'domcontentloaded'
    });
    await page.waitForTimeout(3000);

    // 检查是否已登录
    const isLoggedIn = await page.evaluate(() => {
      // 检查页面是否包含登录表单
      const hasLoginForm = document.body.innerHTML.includes('登录') ||
                          document.body.innerHTML.includes('账号') ||
                          document.body.innerHTML.includes('密码');
      // 检查是否有隐藏区块内容（只有登录用户可见）
      const hasHiddenContent = document.body.innerHTML.includes('智能设计分析') ||
                              document.body.innerHTML.includes('立即开始分析');
      return hasHiddenContent && !hasLoginForm;
    });

    console.log(`   当前登录状态: ${isLoggedIn ? '✅ 已登录' : '❌ 未登录'}`);

    if (!isLoggedIn) {
      console.log('\n⚠️  检测到未登录状态');
      console.log('   请手动执行以下操作：');
      console.log('   1. 在打开的浏览器中登录 WordPress');
      console.log('   2. 登录成功后，测试将自动继续...\n');
      console.log('   等待登录中...');

      // 等待用户手动登录（最多5分钟）
      await page.waitForFunction(
        () => {
          return document.body.innerHTML.includes('智能设计分析') ||
                 document.body.innerHTML.includes('立即开始分析');
        },
        { timeout: 300000 }
      );

      console.log('   ✅ 检测到登录成功！');
    }

    // ==================== 步骤2：检查隐藏区块是否可见 ====================
    console.log('\n✓ 步骤2: 检查WPCOM隐藏区块是否可见');

    const hiddenBlockInfo = await page.evaluate(() => {
      const body = document.body.innerHTML;
      const hasCard = body.includes('智能设计分析') || body.includes('立即开始分析');
      const hasLink = body.includes('localhost:3000') || body.includes('app-entry-link');

      // 尝试找到应用入口链接
      let appLink = null;
      const links = Array.from(document.querySelectorAll('a'));
      for (const link of links) {
        const href = link.getAttribute('href') || '';
        if (href.includes('localhost:3000') || href.includes('nextjs')) {
          appLink = {
            href: href,
            text: link.textContent.trim()
          };
          break;
        }
      }

      return {
        hasCard,
        hasLink,
        appLink
      };
    });

    if (hiddenBlockInfo.hasCard) {
      console.log('   ✅ 隐藏区块可见（用户已登录）');
    } else {
      console.log('   ❌ 隐藏区块不可见');
      console.log('   可能原因：');
      console.log('     1. WPCOM隐藏区块未正确配置');
      console.log('     2. 用户未登录');
      console.log('     3. 会员权限不足');
      await browser.close();
      return;
    }

    if (hiddenBlockInfo.appLink) {
      console.log(`   ✅ 找到应用入口链接: "${hiddenBlockInfo.appLink.text}"`);
      console.log(`   链接地址: ${hiddenBlockInfo.appLink.href}`);

      // 检查链接是否包含 Token
      const hasToken = hiddenBlockInfo.appLink.href.includes('sso_token=');
      if (hasToken) {
        console.log('   ✅ 链接包含 sso_token 参数（修复已生效）');
        const tokenMatch = hiddenBlockInfo.appLink.href.match(/sso_token=([^&]+)/);
        if (tokenMatch) {
          const tokenPreview = tokenMatch[1].substring(0, 20) + '...';
          console.log(`   Token 预览: ${tokenPreview}`);
        }
      } else {
        console.log('   ⚠️  链接不包含 sso_token 参数');
        console.log('   这意味着 JavaScript Token 注入代码尚未部署');
        console.log('   用户需要在 WPCOM 隐藏区块中添加 JavaScript 代码');
      }
    } else {
      console.log('   ❌ 未找到应用入口链接');
      console.log('   请检查 WPCOM 隐藏区块中是否包含应用链接');
      await browser.close();
      return;
    }

    // ==================== 步骤3：点击应用入口链接 ====================
    console.log('\n✓ 步骤3: 点击应用入口链接');

    // 清除之前的错误记录
    errors.length = 0;

    // 点击链接
    const linkSelector = 'a[href*="localhost:3000"], a[id*="app-entry"], a[href*="nextjs"]';
    const appLinkElement = await page.locator(linkSelector).first();

    if (await appLinkElement.count() === 0) {
      console.log('   ❌ 无法定位到应用入口链接元素');
      await browser.close();
      return;
    }

    // 获取链接地址
    const linkHref = await appLinkElement.getAttribute('href');
    console.log(`   点击链接: ${linkHref}`);

    // 点击并等待导航
    await Promise.all([
      page.waitForURL(/localhost:3000/, { timeout: 15000 }),
      appLinkElement.click()
    ]);

    const currentUrl = page.url();
    console.log(`   ✅ 已跳转到: ${currentUrl}`);

    // ==================== 步骤4：验证 URL 是否包含 Token ====================
    console.log('\n✓ 步骤4: 验证 URL 参数');

    const urlHasToken = currentUrl.includes('sso_token=');
    console.log(`   包含 sso_token: ${urlHasToken ? '✅ 是' : '❌ 否'}`);

    if (urlHasToken) {
      const tokenMatch = currentUrl.match(/sso_token=([^&]+)/);
      if (tokenMatch) {
        const tokenPreview = tokenMatch[1].substring(0, 30) + '...';
        console.log(`   Token 值: ${tokenPreview}`);
      }
    }

    // ==================== 步骤5：等待应用加载并检查登录状态 ====================
    console.log('\n✓ 步骤5: 检查应用登录状态');

    await page.waitForTimeout(5000); // 等待 AuthContext 验证 Token

    // 检查是否显示登录界面
    const loginScreenVisible = await page.evaluate(() => {
      const body = document.body.innerText;
      return body.includes('请先登录以使用应用') ||
             body.includes('立即登录') ||
             body.includes('前往登录');
    });

    console.log(`   显示登录界面: ${loginScreenVisible ? '❌ 是（失败）' : '✅ 否（成功）'}`);

    // 检查是否成功进入分析页面
    const onAnalysisPage = page.url().includes('/analysis');
    console.log(`   是否在分析页面: ${onAnalysisPage ? '✅ 是' : '❌ 否'}`);

    // 检查是否有用户信息显示
    const hasUserInfo = await page.evaluate(() => {
      const body = document.body.innerText;
      return body.includes('欢迎') || body.includes('用户') || body.includes('退出登录');
    });
    console.log(`   显示用户信息: ${hasUserInfo ? '✅ 是' : '❌ 否'}`);

    // ==================== 步骤6：检查网络请求错误 ====================
    console.log('\n✓ 步骤6: 检查网络请求错误');

    if (errors.length > 0) {
      console.log(`   ❌ 发现 ${errors.length} 个错误请求:`);
      errors.forEach((err, index) => {
        console.log(`     ${index + 1}. [${err.status}] ${err.url}`);
      });
    } else {
      console.log('   ✅ 无 401/400 错误');
    }

    // ==================== 步骤7：检查浏览器控制台 ====================
    console.log('\n✓ 步骤7: 检查 AuthContext 日志');

    await page.waitForTimeout(2000);

    // ==================== 测试结果汇总 ====================
    console.log('\n' + '='.repeat(70));
    console.log('📊 测试结果汇总');
    console.log('='.repeat(70));

    const allTestsPassed =
      urlHasToken &&          // URL 包含 Token
      !loginScreenVisible &&  // 不显示登录界面
      (onAnalysisPage || hasUserInfo) && // 在分析页面或显示用户信息
      errors.length === 0;    // 无 401/400 错误

    if (allTestsPassed) {
      console.log('\n✅✅✅ 测试通过！跨域Cookie修复生效 ✅✅✅\n');
      console.log('✓ URL 包含 sso_token 参数');
      console.log('✓ 应用自动登录成功');
      console.log('✓ 用户直接进入应用（无登录界面）');
      console.log('✓ 无 401/400 错误');
      console.log('\n🎉 v3.0.20 跨域Cookie修复完全成功！');
    } else {
      console.log('\n❌ 测试未完全通过，请检查以下项目：\n');
      if (!urlHasToken) {
        console.log('❌ URL 不包含 sso_token');
        console.log('   → 需要在 WPCOM 隐藏区块中添加 JavaScript Token 注入代码');
        console.log('   → 参考: CROSS_DOMAIN_COOKIE_FIX.md 方案B');
      }
      if (loginScreenVisible) {
        console.log('❌ 仍然显示登录界面');
        console.log('   → Token 验证可能失败');
        console.log('   → 检查 WordPress REST API 是否正常工作');
      }
      if (!onAnalysisPage && !hasUserInfo) {
        console.log('❌ 未成功进入应用');
        console.log('   → 检查 AuthContext Token 验证逻辑');
      }
      if (errors.length > 0) {
        console.log('❌ 存在网络错误');
        console.log('   → 检查 WordPress SSO 插件配置');
      }
    }

    console.log('\n' + '='.repeat(70));
    console.log('📋 诊断信息');
    console.log('='.repeat(70));
    console.log(`当前 URL: ${page.url()}`);
    console.log(`总请求数: ${requests.length}`);
    console.log(`错误请求数: ${errors.length}`);
    console.log('='.repeat(70));

  } catch (error) {
    console.log(`\n❌ 测试错误: ${error.message}`);
    console.log(`错误堆栈: ${error.stack}`);
  } finally {
    console.log('\n⏸️  浏览器将在 10 秒后关闭，请查看最终状态...');
    await page.waitForTimeout(10000);
    await browser.close();
    console.log('✓ 测试完成\n');
  }
})();
