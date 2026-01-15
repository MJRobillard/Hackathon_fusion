'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/lib/api';

interface DatabasePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Document {
  _id?: string;
  id?: string;
  query?: string;
  created_at?: string;
  [key: string]: any;
}

export function DatabasePanel({ isOpen, onClose }: DatabasePanelProps) {
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  // Fetch collections
  const { data: collections, isLoading: collectionsLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => apiService.getCollections(),
    enabled: isOpen,
  });

  // Fetch documents for selected collection
  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', selectedCollection, page],
    queryFn: () => apiService.getDocuments(selectedCollection, pageSize, page * pageSize),
    enabled: isOpen && !!selectedCollection,
  });

  // Fetch collection count
  const { data: totalCount } = useQuery({
    queryKey: ['collection-count', selectedCollection],
    queryFn: () => apiService.getCollectionCount(selectedCollection),
    enabled: isOpen && !!selectedCollection,
  });

  if (!isOpen) return null;

  const count = totalCount?.count ?? 0;
  const totalPages = count > 0 ? Math.ceil(count / pageSize) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-6xl mx-4 bg-[#14161B] border border-[#1F2937] rounded-lg shadow-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[#1F2937] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-emerald-400" fill="currentColor" viewBox="0 0 24 24">
              <path d="M17.193 9.555c-1.264-5.58-4.252-7.414-4.573-8.115-.28-.394-.53-.954-.735-1.44-.036.495-.055.685-.523 1.184-.723.566-4.438 3.682-4.74 10.02-.282 5.912 4.27 9.435 4.888 9.884l.07.05A73.49 73.49 0 0011.91 24h.481c.114-1.032.284-2.056.51-3.07.417-.296 4.488-3.3 4.488-8.944 0-.954-.126-1.77-.196-2.431z"/>
            </svg>
            <h2 className="text-sm font-semibold text-gray-300 tracking-wide">MONGODB DATABASE</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-[#1F2937] rounded transition-colors"
          >
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Collections List */}
          <div className="w-64 border-r border-[#1F2937] overflow-y-auto">
            <div className="p-3 border-b border-[#1F2937]">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Collections</h3>
            </div>
            {collectionsLoading ? (
              <div className="p-4 text-center">
                <div className="text-xs text-gray-500">Loading...</div>
              </div>
            ) : collections && collections.length > 0 ? (
              <div className="p-2">
                {collections.map((collection) => (
                  <button
                    key={collection}
                    onClick={() => {
                      setSelectedCollection(collection);
                      setSelectedDocument(null);
                      setPage(0);
                    }}
                    className={`w-full text-left px-3 py-2 rounded text-xs transition-colors ${
                      selectedCollection === collection
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-300 hover:bg-[#1F2937]'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                      </svg>
                      <span className="font-mono">{collection}</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center">
                <div className="text-xs text-gray-500">No collections found</div>
              </div>
            )}
          </div>

          {/* Middle: Documents List */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {selectedCollection ? (
              <>
                <div className="p-3 border-b border-[#1F2937] flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
                      {selectedCollection}
                    </h3>
                    {count > 0 && (
                      <p className="text-[10px] text-gray-500 mt-0.5">
                        {count} documents
                      </p>
                    )}
                  </div>
                  {totalPages > 1 && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="p-1 hover:bg-[#1F2937] rounded disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                      </button>
                      <span className="text-[10px] text-gray-400 font-mono">
                        {page + 1} / {totalPages}
                      </span>
                      <button
                        onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="p-1 hover:bg-[#1F2937] rounded disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {documentsLoading ? (
                    <div className="p-4 text-center">
                      <div className="text-xs text-gray-500">Loading documents...</div>
                    </div>
                  ) : documents && documents.length > 0 ? (
                    <div className="space-y-2">
                      {documents.map((doc: Document, index: number) => (
                        <button
                          key={doc._id || index}
                          onClick={() => setSelectedDocument(doc)}
                          className={`w-full text-left p-3 rounded border transition-colors ${
                            selectedDocument === doc
                              ? 'bg-blue-500/10 border-blue-500/30'
                              : 'bg-[#0A0B0D] border-[#1F2937] hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="text-xs font-mono text-gray-300 truncate">
                                {doc._id || doc.id || `Document ${index + 1}`}
                              </div>
                              {doc.query && (
                                <div className="text-[10px] text-gray-500 mt-1 line-clamp-2">
                                  {doc.query}
                                </div>
                              )}
                              {doc.created_at && (
                                <div className="text-[9px] text-gray-600 mt-1">
                                  {new Date(doc.created_at).toLocaleString()}
                                </div>
                              )}
                            </div>
                            <svg className="w-4 h-4 text-gray-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 text-center">
                      <div className="text-xs text-gray-500">No documents found</div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-12 h-12 text-gray-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <p className="text-sm text-gray-500">Select a collection to view documents</p>
                </div>
              </div>
            )}
          </div>

          {/* Right: Document Details */}
          {selectedDocument && (
            <div className="w-96 border-l border-[#1F2937] flex flex-col overflow-hidden">
              <div className="p-3 border-b border-[#1F2937]">
                <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Document Details</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-3">
                <pre className="text-[10px] font-mono text-gray-300 whitespace-pre-wrap break-words">
                  {JSON.stringify(selectedDocument, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

