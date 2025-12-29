export type ModelId = 'fast' | 'smart';

export interface Model {
    id: ModelId;
    name: string;
    description?: string;
}

export const validModels: Model[] = [
    {
        id: 'fast',
        name: 'Axio Fast ⚡',
        description: 'Great for simple tasks & speed'
    },
    {
        id: 'smart',
        name: 'Axio Pro 🧠',
        description: 'Best for reasoning & complex queries'
    },
] as const;
