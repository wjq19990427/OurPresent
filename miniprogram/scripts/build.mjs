import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const sourceRoot = path.join(projectRoot, 'miniprogram')
const outputRoot = path.join(projectRoot, 'dist')
const tscBin = path.join(projectRoot, 'node_modules', '.bin', 'tsc')
const esbuildBin = path.join(projectRoot, 'node_modules', '.bin', 'esbuild')

if (!existsSync(tscBin)) {
  console.error('TypeScript compiler not found. Run `npm install` in miniprogram/ first.')
  process.exit(1)
}

if (!existsSync(esbuildBin)) {
  console.error('esbuild not found. Run `npm install` in miniprogram/ first.')
  process.exit(1)
}

rmSync(outputRoot, { recursive: true, force: true })
mkdirSync(outputRoot, { recursive: true })

const compile = spawnSync(tscBin, ['-p', path.join(projectRoot, 'tsconfig.json')], {
  cwd: projectRoot,
  stdio: 'inherit',
})

if (compile.status !== 0) {
  process.exit(compile.status ?? 1)
}

cpSync(sourceRoot, outputRoot, {
  recursive: true,
  filter: (filePath) => !filePath.endsWith('.ts'),
})

const cryptoBundle = spawnSync(
  esbuildBin,
  [
    path.join(sourceRoot, 'subpackages/crypto/index.js'),
    '--bundle',
    '--format=cjs',
    '--platform=browser',
    '--target=es2020',
    `--outfile=${path.join(outputRoot, 'subpackages/crypto/index.js')}`,
  ],
  {
    cwd: projectRoot,
    stdio: 'inherit',
  }
)

if (cryptoBundle.status !== 0) {
  process.exit(cryptoBundle.status ?? 1)
}
