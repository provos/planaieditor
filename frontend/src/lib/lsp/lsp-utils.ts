import type { Socket } from 'socket.io-client';
import {
    Emitter,
    Event,
    type Disposable,
    type Message,
    type MessageReader,
    type MessageWriter
} from 'vscode-jsonrpc';

// --- LSP Integration - Reader/Writer ---
// Socket.IO Reader/Writer implementation for monaco-languageclient

/**
 * Implements the MessageReader interface for monaco-languageclient,
 * using a Socket.IO connection to receive messages from the backend.
 */
export class SocketIOReader implements MessageReader {
    private socket: Socket;
    private onErrorEmitter = new Emitter<Error>();
    private onCloseEmitter = new Emitter<void>();
    private onMessageEmitter = new Emitter<Message>();

    public readonly onError: Event<Error> = this.onErrorEmitter.event;
    public readonly onClose: Event<void> = this.onCloseEmitter.event;
    // Not typically used, but required by the interface
    public readonly onPartialMessage: Event<any> = new Emitter<any>().event;

    constructor(socket: Socket) {
        this.socket = socket;
        this.socket.on('lsp_response', (message: Message) => {
            console.debug('[LSP Reader] Received:', message);
            try {
                this.onMessageEmitter.fire(message);
            } catch (e) {
                this.onErrorEmitter.fire(e as Error);
            }
        });
        this.socket.on('disconnect', () => {
            console.warn('[LSP Reader] Socket disconnected');
            this.onCloseEmitter.fire();
        });
        this.socket.on('connect_error', (err) => {
            console.error('[LSP Reader] Socket connect error:', err);
            this.onErrorEmitter.fire(err);
        });
        // Listen for specific LSP errors signaled by the backend
        this.socket.on('lsp_error', (err) => {
            console.error('[LSP Reader] Received lsp_error from backend:', err);
            this.onErrorEmitter.fire(new Error(JSON.stringify(err)));
        });
    }

    /** Listens for messages coming from the socket */
    listen(callback: (message: Message) => void): Disposable {
        return this.onMessageEmitter.event(callback);
    }

    /** Cleans up emitters and socket listeners */
    dispose(): void {
        console.log('[LSP Reader] Disposing...');
        this.onErrorEmitter.dispose();
        this.onCloseEmitter.dispose();
        this.onMessageEmitter.dispose();
        // Remove listeners from socket
        this.socket.off('lsp_response');
        this.socket.off('disconnect');
        this.socket.off('connect_error');
        this.socket.off('lsp_error');
    }
}

/**
 * Implements the MessageWriter interface for monaco-languageclient,
 * using a Socket.IO connection to send messages to the backend.
 */
export class SocketIOWriter implements MessageWriter {
    private socket: Socket;
    private onErrorEmitter = new Emitter<[Error, Message | undefined, number | undefined]>();
    private onCloseEmitter = new Emitter<void>();

    public readonly onError: Event<[Error, Message | undefined, number | undefined]> =
        this.onErrorEmitter.event;
    public readonly onClose: Event<void> = this.onCloseEmitter.event;

    constructor(socket: Socket) {
        this.socket = socket;
        this.socket.on('disconnect', () => {
            console.warn('[LSP Writer] Socket disconnected');
            this.onCloseEmitter.fire();
        });
        // Forward socket errors to the language client
        this.socket.on('connect_error', (err) => {
            console.error('[LSP Writer] Socket connect error:', err);
            this.onErrorEmitter.fire([err, undefined, undefined]);
        });
        this.socket.on('error', (err) => {
            console.error('[LSP Writer] Socket error:', err);
            this.onErrorEmitter.fire([err, undefined, undefined]);
        });
    }

    /** Sends a message via the socket */
    async write(message: Message): Promise<void> {
        console.debug('[LSP Writer] Sending:', message);
        try {
            this.socket.emit('lsp_message', message);
            return Promise.resolve(); // Assume success immediately
        } catch (error) {
            this.onErrorEmitter.fire([error as Error, message, undefined]);
            return Promise.reject(error);
        }
    }

    /** Called by the language client on shutdown */
    end(): void {
        // Optional: Signal backend? Usually handled by socket disconnect/stop_lsp event.
        console.log('[LSP Writer] end() called.');
    }

    /** Cleans up emitters and socket listeners */
    dispose(): void {
        console.log('[LSP Writer] Disposing...');
        this.onErrorEmitter.dispose();
        this.onCloseEmitter.dispose();
        // Remove listeners from socket
        this.socket.off('disconnect');
        this.socket.off('connect_error');
        this.socket.off('error');
    }
}
