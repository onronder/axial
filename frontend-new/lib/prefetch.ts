import type { QueryClient } from "@tanstack/react-query";
import { CHAT_HISTORY_KEY, fetchConversations } from "@/hooks/useChatHistory";
import { documentsQueryKey, fetchDocuments } from "@/hooks/useDocuments";

const DEFAULT_PAGE = 1;
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_SEARCH = "";

export async function prefetchDashboardData(queryClient: QueryClient): Promise<void> {
  await Promise.allSettled([
    queryClient.prefetchQuery({
      queryKey: CHAT_HISTORY_KEY,
      queryFn: ({ signal }) => fetchConversations(signal),
      staleTime: 5 * 60 * 1000,
    }),
    queryClient.prefetchQuery({
      queryKey: documentsQueryKey(DEFAULT_PAGE, DEFAULT_PAGE_SIZE, DEFAULT_SEARCH),
      queryFn: ({ signal }) =>
        fetchDocuments({ page: DEFAULT_PAGE, pageSize: DEFAULT_PAGE_SIZE, search: DEFAULT_SEARCH, signal }),
      staleTime: 5 * 60 * 1000,
    }),
  ]);
}
