import { deriveSessionTitle, limitSessionTitle, resolveSessionTitle } from '@/lib/sessionTitle';

describe('session title helpers', () => {
  it('keeps enough title text for the sidebar field to use its available width', () => {
    expect(limitSessionTitle('请系统分析农耕文化与城市化进程中的空间关系')).toBe('请系统分析农耕文化与城市化进程中的空间关系');
  });

  it('keeps original title content after punctuation so the sidebar width decides the visible cut', () => {
    expect(deriveSessionTitle('深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场连接处，打算做奶茶店。')).toBe(
      '深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场连接处，打算做奶茶店。'
    );
  });

  it('keeps short original input instead of padding it with generic templates', () => {
    expect(deriveSessionTitle('深圳商业方案')).toBe('深圳商业方案');
  });

  it('replaces generic generated display names with the original input title', () => {
    expect(
      resolveSessionTitle(
        '深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。',
        '深圳预算需求摘要'
      )
    ).toBe('深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。');
  });

  it('replaces longer generic generated display names with the original input title', () => {
    expect(resolveSessionTitle('深圳商业方案', '深圳商业项目方案建议梳理')).toBe('深圳商业方案');
  });

  it('replaces stale prefix display names with a fuller original input title', () => {
    expect(
      resolveSessionTitle(
        '深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。',
        '深圳市南山区来福士广场'
      )
    ).toBe('深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。');
  });

  it('replaces longer stale prefix display names with a fuller original input title', () => {
    expect(
      resolveSessionTitle(
        '请系统分析农耕文化与城市化进程如何影响当代室内设计概念结构，给出策略。',
        '请系统分析农耕文化与城市化进程'
      )
    ).toBe('请系统分析农耕文化与城市化进程如何影响当代室内设计概念结构，给出策略。');
  });
});
