import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
import type { Socket } from 'socket.io-client';
import { SocketIOReader, SocketIOWriter } from './lsp-utils';
import type { MonacoLanguageClient } from 'monaco-languageclient';
import type { MessageTransports, LanguageClientOptions } from 'vscode-languageclient/browser.js';
// import { ErrorAction as VscodeErrorAction, CloseAction as VscodeCloseAction } from 'vscode-languageclient/lib/common/client';

// Dynamically imported MonacoLanguageClient constructor type
type MonacoLanguageClientConstructorType = {
    new(args: {
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

    constructor(
        private socket: Socket,
        private monacoInstanceRef: typeof Monaco,
    ) { }

    public async start(): Promise<void> {
        if (this.isStarted || this.startPromise) {
            console.log(`[LSP Manager] Start already in progress or completed.`);
            return this.startPromise;
        }

        console.log(`[LSP Manager] Starting LSP connection...`);
        this.startPromise = this._initializeAndStart();

        try {
            await this.startPromise;
            this.isStarted = true;
            console.log(`[LSP Manager] LSP connection started successfully.`);
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
            console.log(`[LSP Manager] Dynamically importing MonacoLanguageClient...`);
            try {
                // Ensure MonacoLanguageClient is correctly imported
                const clientModule = await import('monaco-languageclient');
                // Adjust based on actual export structure if necessary
                this.MonacoLanguageClientConstructor =
                    clientModule.MonacoLanguageClient || (clientModule as any).default;
                if (!this.MonacoLanguageClientConstructor) {
                    throw new Error(
                        'MonacoLanguageClient constructor not found in the imported module.'
                    );
                }
                console.log(
                    `[LSP Manager] MonacoLanguageClient imported successfully.`
                );
            } catch (err) {
                console.error(
                    `[LSP Manager] Failed to dynamically import MonacoLanguageClient:`,
                    err
                );
                throw err; // Propagate error
            }
        }

        // 2. Dispose existing reader/writer (safety net)
        this.reader?.dispose();
        this.writer?.dispose();

        // 3. Create new reader/writer
        console.log(`[LSP Manager] Creating SocketIO reader/writer...`);
        this.reader = new SocketIOReader(this.socket);
        this.writer = new SocketIOWriter(this.socket);
        const transports: MessageTransports = { reader: this.reader, writer: this.writer };

        // 4. Create Language Client
        console.log(`[LSP Manager] Creating language client...`);
        try {
            this.languageClient = this._createLanguageClient(
                transports,
                this.MonacoLanguageClientConstructor
            );
            console.log(`[LSP Manager] Language client created.`);
        } catch (error) {
            console.error(`[LSP Manager] Error creating language client:`, error);
            this.reader?.dispose(); // Clean up transports if client creation fails
            this.writer?.dispose();
            this.reader = undefined;
            this.writer = undefined;
            throw error;
        }

        // 5. Start the client
        console.log(`[LSP Manager] Starting language client...`);
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
                error: () => ({ action: VscodeErrorAction.Continue }),
                closed: () => ({ action: VscodeCloseAction.DoNotRestart })
            },
            workspaceFolder: {
                uri: this.monacoInstanceRef.Uri.parse('/workspace'),
                name: 'workspace',
                index: 0
            },
            initializationOptions: {}
        };

        return new ClientConstructor({
            name: `Python Language Client`,
            clientOptions: clientOptions,
            messageTransports: transports
        });
    }

    public async stop(): Promise<void> {
        if (!this.isStarted && !this.startPromise) {
            console.log(`[LSP Manager] LSP Manager already stopped or never started.`);
            return;
        }
        console.log(`[LSP Manager] Stopping LSP connection...`);

        // Ensure any ongoing start process is awaited before stopping
        if (this.startPromise) {
            try {
                await this.startPromise;
            } catch (e) {
                console.warn(
                    `[LSP Manager] Error during pending start operation while stopping:`,
                    e
                );
            }
        }

        const stopClientPromise = this.languageClient?.stop().catch((e) => {
            console.error(`[LSP Manager] Error stopping language client:`, e);
        });

        this.reader?.dispose();
        this.writer?.dispose();

        await stopClientPromise; // Wait for client stop after disposing transports

        console.log(`[LSP Manager] LSP connection stopped.`);

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