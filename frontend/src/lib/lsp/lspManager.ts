import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
import type { Socket } from 'socket.io-client';
import { SocketIOReader, SocketIOWriter } from './lsp-utils';
import type { MonacoLanguageClient } from 'monaco-languageclient';
import type { MessageTransports, LanguageClientOptions } from 'vscode-languageclient/browser.js';

// Dynamically imported MonacoLanguageClient constructor type
type MonacoLanguageClientConstructorType = {
	new (args: {
		name: string;
		clientOptions: LanguageClientOptions;
		messageTransports: MessageTransports;
	}): MonacoLanguageClient;
};

export class LspManager {
	private languageClient: MonacoLanguageClient | undefined;
	private reader: SocketIOReader | undefined;
	private writer: SocketIOWriter | undefined;
	private MonacoLanguageClientConstructor: MonacoLanguageClientConstructorType | undefined;
	private isStarted = false;
	private startPromise: Promise<void> | undefined;
	private continue: number = -1;
	private doNotRestart: number = -1;

	constructor(
		private socket: Socket,
		private monacoInstanceRef: typeof Monaco
	) {}

	public async start(): Promise<void> {
		if (this.isStarted || this.startPromise) {
			console.debug(`[LSP Manager] Start already in progress or completed.`);
			return this.startPromise;
		}

		// Need to dynamically import because of SSR
		const { ErrorAction, CloseAction } = await import('vscode-languageclient/lib/common/client');
		this.continue = ErrorAction.Continue;
		this.doNotRestart = CloseAction.DoNotRestart;

		console.debug(`[LSP Manager] Starting LSP connection...`);
		this.startPromise = this._initializeAndStart();

		try {
			await this.startPromise;
			this.isStarted = true;
			console.debug(`[LSP Manager] LSP connection started successfully.`);
		} catch (error) {
			console.error(`[LSP Manager] Failed to start LSP connection:`, error);
			this.startPromise = undefined; // Reset promise on failure
			// Ensure cleanup happens even if start fails midway
			await this.stop();
			throw error; // Re-throw error after cleanup
		}
	}

	private async _initializeAndStart(): Promise<void> {
		// 1. Dynamically import MonacoLanguageClient if needed
		if (!this.MonacoLanguageClientConstructor) {
			console.debug(`[LSP Manager] Dynamically importing MonacoLanguageClient...`);
			try {
				// Ensure MonacoLanguageClient is correctly imported
				const clientModule = await import('monaco-languageclient');
				// Adjust based on actual export structure if necessary
				this.MonacoLanguageClientConstructor =
					clientModule.MonacoLanguageClient || (clientModule as any).default;
				if (!this.MonacoLanguageClientConstructor) {
					throw new Error('MonacoLanguageClient constructor not found in the imported module.');
				}
				console.debug(`[LSP Manager] MonacoLanguageClient imported successfully.`);
			} catch (err) {
				console.error(`[LSP Manager] Failed to dynamically import MonacoLanguageClient:`, err);
				throw err; // Propagate error
			}
		}

		// 2. Dispose existing reader/writer (safety net)
		this.reader?.dispose();
		this.writer?.dispose();

		// 3. Create new reader/writer
		console.debug(`[LSP Manager] Creating SocketIO reader/writer...`);
		this.reader = new SocketIOReader(this.socket);
		this.writer = new SocketIOWriter(this.socket);
		const transports: MessageTransports = { reader: this.reader, writer: this.writer };

		// 4. Create Language Client
		console.debug(`[LSP Manager] Creating language client...`);
		try {
			this.languageClient = this._createLanguageClient(
				transports,
				this.MonacoLanguageClientConstructor
			);
			console.debug(`[LSP Manager] Language client created.`);
		} catch (error) {
			console.error(`[LSP Manager] Error creating language client:`, error);
			this.reader?.dispose(); // Clean up transports if client creation fails
			this.writer?.dispose();
			this.reader = undefined;
			this.writer = undefined;
			throw error;
		}

		// 5. Start the client
		console.debug(`[LSP Manager] Starting language client...`);
		await this.languageClient.start(); // Wait for the start promise to resolve

		// 6. Handle reader closure (e.g., socket disconnect)
		this.reader.onClose(async () => {
			console.warn(`[LSP Manager] LSP Reader closed. Stopping client.`);
			await this.stop(); // Stop manager if reader closes
		});
	}

	private _createLanguageClient(
		transports: MessageTransports,
		ClientConstructor: MonacoLanguageClientConstructorType
	): MonacoLanguageClient {
		const clientOptions: LanguageClientOptions = {
			documentSelector: ['python'], // Hardcoded to python
			errorHandler: {
				error: () => ({ action: this.continue }),
				closed: () => ({ action: this.doNotRestart })
			},
			workspaceFolder: {
				uri: this.monacoInstanceRef.Uri.parse('/workspace'),
				name: 'workspace',
				index: 0
			},
			initializationOptions: {
				jediSettings: {
					debug: false,
					autoImportModules: ['planai']
				}
			}
		};

		return new ClientConstructor({
			name: `Python Language Client`,
			clientOptions: clientOptions,
			messageTransports: transports
		});
	}

	public async stop(): Promise<void> {
		if (!this.isStarted && !this.startPromise) {
			console.debug(`[LSP Manager] LSP Manager already stopped or never started.`);
			return;
		}
		console.debug(`[LSP Manager] Stopping LSP connection...`);

		// Ensure any ongoing start process is awaited before stopping
		if (this.startPromise) {
			try {
				await this.startPromise;
			} catch (e) {
				console.warn(`[LSP Manager] Error during pending start operation while stopping:`, e);
				// Even if startPromise failed, languageClient might have been partially initialized
			}
		}

		// Stop the language client first, allowing it to use transports for shutdown
		if (this.languageClient) {
			try {
				console.debug(`[LSP Manager] Attempting to stop the language client...`);
				await this.languageClient.stop();
				console.debug(`[LSP Manager] Language client stopped.`);
			} catch (e) {
				console.error(`[LSP Manager] Error stopping language client:`, e);
			}
		}

		// Then, dispose the transports
		if (this.reader) {
			try {
				this.reader.dispose();
				console.debug(`[LSP Manager] SocketIOReader disposed.`);
			} catch (e) {
				console.error(`[LSP Manager] Error disposing SocketIOReader:`, e);
			}
		}
		if (this.writer) {
			try {
				this.writer.dispose();
				console.debug(`[LSP Manager] SocketIOWriter disposed.`);
			} catch (e) {
				console.error(`[LSP Manager] Error disposing SocketIOWriter:`, e);
			}
		}

		console.debug(`[LSP Manager] LSP connection resources released.`);

		// Reset state
		this.languageClient = undefined;
		this.reader = undefined;
		this.writer = undefined;
		this.isStarted = false;
		this.startPromise = undefined;
	}

	public get isClientStarted(): boolean {
		return this.isStarted;
	}
}
