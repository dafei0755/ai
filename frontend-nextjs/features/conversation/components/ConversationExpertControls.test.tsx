import { existsSync } from 'fs';
import path from 'path';

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const expertControlsPath = path.join(__dirname, 'ExpertControls.tsx');

const loadExpertControls = () => {
  expect(existsSync(expertControlsPath)).toBe(true);

  const { ExpertControls } = require('./ExpertControls') as typeof import('./ExpertControls');
  return ExpertControls;
};

describe('conversation expert controls', () => {
  it('renders nothing when no expert controls are configured', () => {
    const ExpertControls = loadExpertControls();

    const { container } = render(
      <ExpertControls
        activeExpertPerspective="默认综合"
        expertPerspectiveOptions={[]}
        summonOptions={[]}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders expert perspective choices and summons an expert once selected', async () => {
    const user = userEvent.setup();
    const onExpertPerspectiveChange = jest.fn();
    const onSummonExpert = jest.fn();
    const ExpertControls = loadExpertControls();

    render(
      <ExpertControls
        activeExpertPerspective="默认综合"
        expertPerspectiveOptions={['默认综合', '运营视角']}
        onExpertPerspectiveChange={onExpertPerspectiveChange}
        summonOptions={['结构顾问', '品牌顾问']}
        onSummonExpert={onSummonExpert}
      />,
    );

    await user.selectOptions(screen.getByRole('combobox', { name: '选择专家视角' }), '运营视角');
    await user.click(screen.getByRole('button', { name: '召集团队' }));
    await user.click(screen.getByRole('button', { name: '结构顾问' }));

    expect(onExpertPerspectiveChange).toHaveBeenCalledWith('运营视角');
    expect(onSummonExpert).toHaveBeenCalledWith('结构顾问');
    expect(screen.queryByRole('button', { name: '品牌顾问' })).not.toBeInTheDocument();
  });

  it('closes the summon menu on outside click and escape', async () => {
    const user = userEvent.setup();
    const ExpertControls = loadExpertControls();

    render(
      <div>
        <button type="button">外部按钮</button>
        <ExpertControls
          activeExpertPerspective="默认综合"
          expertPerspectiveOptions={['默认综合']}
          summonOptions={['结构顾问']}
        />
      </div>,
    );

    await user.click(screen.getByRole('button', { name: '召集团队' }));
    expect(screen.getByRole('button', { name: '结构顾问' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '外部按钮' }));
    expect(screen.queryByRole('button', { name: '结构顾问' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '召集团队' }));
    expect(screen.getByRole('button', { name: '结构顾问' })).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('button', { name: '结构顾问' })).not.toBeInTheDocument();
  });
});
