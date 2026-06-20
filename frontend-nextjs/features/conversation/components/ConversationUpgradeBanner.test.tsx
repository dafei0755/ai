import { existsSync } from 'fs';
import path from 'path';

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const upgradeBannerPath = path.join(__dirname, 'UpgradeBanner.tsx');

const loadUpgradeBanner = () => {
  expect(existsSync(upgradeBannerPath)).toBe(true);

  const { UpgradeBanner } = require('./UpgradeBanner') as typeof import('./UpgradeBanner');
  return UpgradeBanner;
};

describe('conversation upgrade banner', () => {
  it('renders upgrade copy and calls confirm and dismiss actions', async () => {
    const user = userEvent.setup();
    const onUpgradeConfirm = jest.fn();
    const onUpgradeDismiss = jest.fn();
    const UpgradeBanner = loadUpgradeBanner();

    render(
      <UpgradeBanner
        adaptiveChatGutter="16px"
        onUpgradeConfirm={onUpgradeConfirm}
        onUpgradeDismiss={onUpgradeDismiss}
      />,
    );

    expect(screen.getByText('对话已积累足够上下文，可以整理为正式项目')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '立即整理' }));
    await user.click(screen.getByRole('button', { name: '稍后' }));

    expect(onUpgradeConfirm).toHaveBeenCalledTimes(1);
    expect(onUpgradeDismiss).toHaveBeenCalledTimes(1);
  });
});
