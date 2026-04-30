#!/usr/bin/env node
/*
 * Safe frontend dev launcher for Windows.
 * - Detects PID(s) listening on the target port
 * - Kills only stale Next.js dev/start-server node processes
 * - Starts `npm run dev` afterward
 */

const { execSync, spawn } = require('child_process');

const targetPort = Number(process.env.FRONTEND_PORT || 3001);

function run(command) {
  return execSync(command, {
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'pipe'],
  });
}

function listListeningPids(port) {
  try {
    const output = run(`netstat -ano -p tcp | findstr :${port}`);
    const lines = output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .filter((line) => line.includes('LISTENING'));

    const pids = new Set();
    for (const line of lines) {
      const parts = line.split(/\s+/);
      const pid = Number(parts[parts.length - 1]);
      if (Number.isFinite(pid) && pid > 0) {
        pids.add(pid);
      }
    }
    return [...pids];
  } catch {
    return [];
  }
}

function getProcessInfo(pid) {
  // First try tasklist for stable process-name lookup on Windows.
  let baseInfo = null;
  try {
    const output = run(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`).trim();
    if (output && !/^INFO:\s+No tasks are running/i.test(output)) {
      const normalized = output.replace(/^"|"$/g, '').split('","');
      const name = String(normalized[0] || '').trim();
      if (name) {
        baseInfo = {
          pid: Number(pid),
          name,
          commandLine: '',
        };
      }
    }
  } catch {
    // Ignore and fallback to PowerShell query.
  }

  try {
    const ps = [
      `$targetPid = ${pid}`,
      '$p = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $targetPid }',
      'if ($null -ne $p) {',
      '  [pscustomobject]@{',
      '    ProcessId = $p.ProcessId',
      '    Name = $p.Name',
      '    CommandLine = $p.CommandLine',
      '  } | ConvertTo-Json -Compress',
      '}',
    ].join('; ');

    const output = run(
      `powershell -NoProfile -Command "${ps.replace(/"/g, '\\"')}"`
    ).trim();

    if (!output) return baseInfo;
    const parsed = JSON.parse(output);
    const info = {
      pid: Number(parsed.ProcessId),
      name: String(parsed.Name || ''),
      commandLine: String(parsed.CommandLine || ''),
    };

    if (info.commandLine) {
      return info;
    }

    if (baseInfo && baseInfo.commandLine) {
      return baseInfo;
    }

    // Fallback: some Windows setups restrict CIM command line access.
    // WMIC is deprecated but still available on many Win10/11 machines.
    try {
      const wmicOutput = run(`wmic process where processid=${pid} get CommandLine /value`).trim();
      const line = wmicOutput
        .split(/\r?\n/)
        .map((v) => v.trim())
        .find((v) => v.toLowerCase().startsWith('commandline='));

      if (line) {
        const commandLine = line.slice('CommandLine='.length).trim();
        return {
          ...info,
          commandLine,
        };
      }
    } catch {
      // Ignore WMIC fallback errors.
    }

    return info;
  } catch {
    return baseInfo;
  }
}

function isNextNodeProcess(info) {
  if (!info) return false;
  const cmd = info.commandLine.toLowerCase();
  const isNode = info.name.toLowerCase() === 'node.exe' || info.name.toLowerCase() === 'node';
  const looksLikeNext =
    cmd.includes('next\\dist\\server\\lib\\start-server.js') ||
    cmd.includes('next/dist/server/lib/start-server.js') ||
    cmd.includes(' next dev') ||
    cmd.includes('\\next\\dist\\bin\\next');
  return isNode && looksLikeNext;
}

function isNodeProcess(info) {
  if (!info) return false;
  const name = info.name.toLowerCase();
  return name === 'node.exe' || name === 'node';
}

function killPid(pid) {
  run(`taskkill /PID ${pid} /F`);
}

function startDev() {
  const child = spawn('cmd.exe', ['/c', 'npm run dev'], {
    stdio: 'inherit',
    shell: false,
  });

  child.on('exit', (code) => {
    process.exit(code ?? 0);
  });
}

function main() {
  console.log(`[dev:safe] Checking port ${targetPort} ...`);
  const pids = listListeningPids(targetPort);

  if (pids.length === 0) {
    console.log(`[dev:safe] Port ${targetPort} is free.`);
    startDev();
    return;
  }

  const blockedInfos = pids.map(getProcessInfo).filter(Boolean);
  if (blockedInfos.length === 0) {
    console.error(`[dev:safe] Port ${targetPort} is in use, but process info could not be resolved.`);
    console.error(`[dev:safe] PID candidates: ${pids.join(', ')}`);
    console.error(`[dev:safe] Please run: netstat -ano | findstr :${targetPort}`);
    process.exit(1);
    return;
  }

  const killable = blockedInfos.filter(isNextNodeProcess);
  const nonKillable = blockedInfos.filter((info) => !isNextNodeProcess(info));

  // Pragmatic fallback:
  // if exactly one listener exists and it is a node process with unknown cmdline,
  // treat it as stale dev server on the configured frontend port.
  if (killable.length === 0 && nonKillable.length === 1 && isNodeProcess(nonKillable[0])) {
    const only = nonKillable[0];
    const cmd = (only.commandLine || '').trim();
    if (!cmd) {
      console.warn(`[dev:safe] PID=${only.pid} is node.exe on port ${targetPort} with empty command line.`);
      console.warn('[dev:safe] Treating it as stale frontend process and reclaiming the port.');
      killable.push(only);
      nonKillable.length = 0;
    }
  }

  if (nonKillable.length > 0) {
    console.error(`[dev:safe] Port ${targetPort} is occupied by non-Next process(es):`);
    for (const info of nonKillable) {
      console.error(`  - PID=${info.pid} Name=${info.name}`);
      if (info.commandLine) {
        console.error(`    CommandLine=${info.commandLine}`);
      }
    }
    console.error('[dev:safe] Not killing unknown process automatically.');
    process.exit(1);
    return;
  }

  for (const info of killable) {
    console.log(`[dev:safe] Killing stale Next process PID=${info.pid} ...`);
    killPid(info.pid);
  }

  console.log('[dev:safe] Starting frontend dev server ...');
  startDev();
}

main();
