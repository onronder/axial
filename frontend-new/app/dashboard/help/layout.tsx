import { getAllArticles, getCategories } from '@/lib/help';
import { HelpLayoutClient } from './_components/HelpLayoutClient';

export default function HelpLayout({ children }: { children: React.ReactNode }) {
    const articles = getAllArticles();
    const categories = getCategories();
    return (
        <HelpLayoutClient articles={articles} categories={categories}>
            {children}
        </HelpLayoutClient>
    );
}
