import fs from 'fs';
import path from 'path';

const adminPagesToCheck = [
  'concept-maps/page.tsx',
  'conversations/page.tsx',
  'monitoring/page.tsx',
  'tools/page.tsx',
];

describe('Admin API boundary', () => {
  it('does not hardcode backend localhost API hosts inside admin pages', () => {
    for (const relativePath of adminPagesToCheck) {
      const filePath = path.join(process.cwd(), 'app', 'admin', relativePath);
      const source = fs.readFileSync(filePath, 'utf8');

      expect(source).not.toMatch(/http:\/\/localhost:8000\/api/);
      expect(source).not.toMatch(/http:\/\/127\.0\.0\.1:8000\/api/);
    }
  });

  it('does not probe Grafana localhost unless a Grafana URL is configured', () => {
    const source = fs.readFileSync(path.join(process.cwd(), 'app', 'admin', 'monitoring', 'page.tsx'), 'utf8');

    expect(source).not.toContain("process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3200'");
  });
});
