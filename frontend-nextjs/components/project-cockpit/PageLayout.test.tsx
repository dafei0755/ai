import fs from 'fs';
import path from 'path';

describe('project cockpit workspace layout CSS', () => {
  const globalsCss = fs.readFileSync(
    path.join(process.cwd(), 'app', 'globals.css'),
    'utf8',
  );

  it('does not reserve an empty middle column when the cockpit has no middle panel', () => {
    const twoColumnRule = globalsCss.match(
      /\.project-workspace-three-column-shell-two-column\s*\{[\s\S]*?\}/,
    )?.[0];

    expect(twoColumnRule).toBeTruthy();
    expect(twoColumnRule).toContain('grid-template-columns');
    expect(twoColumnRule).toContain('minmax(0, 1fr)');
    expect(twoColumnRule).toContain('var(--workspace-advisor-column-width)');
    expect(twoColumnRule).not.toContain('var(--workspace-middle-column-width)');
  });

  it('keeps information and advisor columns readable by default', () => {
    const shellRule = globalsCss.match(
      /\.project-workspace-three-column-shell\s*\{[\s\S]*?\}/,
    )?.[0];

    expect(shellRule).toBeTruthy();
    expect(shellRule).toContain('--workspace-main-column-width: 56vw');
    expect(shellRule).toContain('--workspace-middle-column-width: 22vw');
    expect(shellRule).toContain('--workspace-advisor-column-width: 22vw');
  });
});
