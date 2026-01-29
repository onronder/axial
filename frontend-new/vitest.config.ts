import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: './__tests__/setup.ts',
        include: ['__tests__/**/*.test.{ts,tsx}'],
        // Memory optimization for OOM issues
        pool: 'forks',
        poolOptions: {
            forks: {
                singleFork: false,
                isolate: true,
            },
        },
        // Enable file parallelization with limited workers
        fileParallelism: true,
        maxWorkers: 3,
        // Increase test timeout
        testTimeout: 30000,
        // Clear mocks between tests
        clearMocks: true,
        // Restore mocks between tests
        restoreMocks: true,
        // Disable transforms caching to reduce memory
        cache: false,
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            all: false,
            exclude: [
                'node_modules/',
                '.next/',
                '__tests__/',
                '*.config.*',
            ],
        },
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './'),
        },
    },
});
