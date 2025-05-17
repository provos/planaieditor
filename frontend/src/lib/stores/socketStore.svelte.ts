import { Socket } from 'socket.io-client';

export const socketStore = $state({
	socket: null as Socket | null,
	isConnected: false
});
