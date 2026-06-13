import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
        plugins: [svelte()],
        base: './', // relative asset URLs -> portable bundle, servable from any path
});
