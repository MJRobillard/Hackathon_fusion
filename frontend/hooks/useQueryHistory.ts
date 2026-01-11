'use client';

import { useState, useCallback } from 'react';
import type { QueryData } from '@/lib/types';

export function useQueryHistory() {
  const [queries, setQueries] = useState<QueryData[]>([]);

  const addQuery = useCallback((query: QueryData) => {
    setQueries((prev) => {
      // Check if query already exists
      const exists = prev.find((q) => q.query_id === query.query_id);
      if (exists) {
        // Update existing query
        return prev.map((q) =>
          q.query_id === query.query_id ? { ...q, ...query } : q
        );
      }
      // Add new query at the beginning
      return [query, ...prev];
    });
  }, []);

  const updateQuery = useCallback((queryId: string, updates: Partial<QueryData>) => {
    setQueries((prev) =>
      prev.map((q) =>
        q.query_id === queryId ? { ...q, ...updates } : q
      )
    );
  }, []);

  const getQuery = useCallback(
    (queryId: string) => {
      return queries.find((q) => q.query_id === queryId);
    },
    [queries]
  );

  return { queries, addQuery, updateQuery, getQuery };
}

