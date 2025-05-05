import tailwindcss from '@tailwindcss/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { sveltePhosphorOptimize } from "phosphor-svelte/vite";
import fs from 'fs';
import url from 'url';


export default defineConfig({
	plugins: [sveltePhosphorOptimize(), tailwindcss(), sveltekit()],
	test: {
		workspace: [
			{
				extends: './vite.config.ts',
				plugins: [svelteTesting()],
				test: {
					name: 'client',
					environment: 'jsdom',
					clearMocks: true,
					include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
					exclude: ['src/lib/server/**'],
					setupFiles: ['./vitest-setup-client.ts']
				}
			},
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	},
	optimizeDeps: {
		exclude: [
			'bits-ui', 'svelte', '@xyflow', 'phosphor-svelte'
		],
		esbuildOptions: {
			plugins: [{
				name: 'import.meta.url',
				setup({ onLoad }) {
					// Help vite that bundles/move files in dev mode without touching `import.meta.url` which breaks asset urls
					onLoad({ filter: /.*\.js/, namespace: 'file' }, async args => {
						const code = fs.readFileSync(args.path, 'utf8')

						const assetImportMetaUrlRE = /\bnew\s+URL\s*\(\s*('[^']+'|"[^"]+"|`[^`]+`)\s*,\s*import\.meta\.url\s*(?:,\s*)?\)/g
						let i = 0
						let newCode = ''
						for (let match = assetImportMetaUrlRE.exec(code); match != null; match = assetImportMetaUrlRE.exec(code)) {
							newCode += code.slice(i, match.index)

							const path = match[1].slice(1, -1)
							const resolved = await import.meta.resolve!(path, url.pathToFileURL(args.path))

							newCode += `new URL(${JSON.stringify(url.fileURLToPath(resolved))}, import.meta.url)`

							i = assetImportMetaUrlRE.lastIndex
						}
						newCode += code.slice(i)

						return { contents: newCode }
					})
				}
			}]
		}
	}
});
