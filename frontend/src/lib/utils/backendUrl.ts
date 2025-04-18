// Import SvelteKit environment helper
import { dev } from '$app/environment';

// Define backend URL based on environment
export const backendUrl = dev ? 'http://localhost:5001' : ''; // Use explicit URL in dev
