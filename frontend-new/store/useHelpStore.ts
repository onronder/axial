/**
 * Help Store
 * 
 * Zustand store for Help Center modal state.
 */

import { create } from 'zustand';
import type { HelpArticle } from '@/data/helpArticles';

interface HelpState {
    isOpen: boolean;
    searchQuery: string;
    selectedArticle: HelpArticle | null;
    selectedCategory: HelpArticle['category'] | 'All';
}

interface HelpActions {
    openHelp: () => void;
    closeHelp: () => void;
    setSearchQuery: (query: string) => void;
    setSelectedArticle: (article: HelpArticle | null) => void;
    setSelectedCategory: (category: HelpArticle['category'] | 'All') => void;
    reset: () => void;
}

const initialState: HelpState = {
    isOpen: false,
    searchQuery: '',
    selectedArticle: null,
    selectedCategory: 'All',
};

export const useHelpStore = create<HelpState & HelpActions>((set) => ({
    ...initialState,

    openHelp: () => set({ isOpen: true }),
    closeHelp: () => set({ isOpen: false, searchQuery: '', selectedArticle: null }),
    setSearchQuery: (searchQuery) => set({ searchQuery }),
    setSelectedArticle: (selectedArticle) => set({ selectedArticle }),
    setSelectedCategory: (selectedCategory) => set({ selectedCategory, selectedArticle: null }),
    reset: () => set(initialState),
}));
