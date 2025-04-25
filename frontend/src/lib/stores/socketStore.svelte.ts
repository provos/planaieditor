import { Socket } from 'socket.io-client';

export let socketStore = $state({
    socket: null as Socket | null,
});