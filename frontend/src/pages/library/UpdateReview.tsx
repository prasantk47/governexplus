import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  ArrowPathIcon, CheckCircleIcon, XCircleIcon,
  ClockIcon, DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

interface PendingUpdate {
  id: string;
  template_item_id: string;
  pending_update_version: string;
  global_version: string;
  global_payload: Record<string, unknown>;
  item?: {
    item_code: string;
    name: string;
    module: string;
    item_type: string;
  };
  is_customized: boolean;
  copy_payload?: Record<string, unknown>;
}

interface DiffData {
  item_code: string;
  global_version: string;
  pending_update_version: string;
  tenant_payload: Record<string, unknown> | null;
  global_payload: Record<string, unknown>;
  is_customized: boolean;
}

export default function UpdateReview() {
  const [selectedUpdate, setSelectedUpdate] = useState<PendingUpdate | null>(null);
  const [diffData, setDiffData] = useState<DiffData | null>(null);
  const [decision, setDecision] = useState<'accept' | 'reject' | 'defer' | ''>('');
  const [notes, setNotes] = useState('');
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['pending-updates'],
    queryFn: () => api.get('/library/pending-updates').then(r => r.data),
  });

  const updates: PendingUpdate[] = data?.updates || [];

  const loadDiff = async (update: PendingUpdate) => {
    setSelectedUpdate(update);
    setDecision('');
    setNotes('');
    try {
      const res = await api.get(`/library/items/${update.template_item_id}/diff`);
      setDiffData(res.data);
    } catch {
      setDiffData(null);
    }
  };

  const reviewMutation = useMutation({
    mutationFn: ({ itemId, dec, n }: { itemId: string; dec: string; n: string }) =>
      api.post(`/library/items/${itemId}/review-update`, { decision: dec, notes: n }),
    onSuccess: (_, vars) => {
      toast.success(`Update ${vars.dec}ed`);
      qc.invalidateQueries({ queryKey: ['pending-updates'] });
      setSelectedUpdate(null);
      setDiffData(null);
    },
    onError: () => toast.error('Review failed'),
  });

  const handleSubmit = () => {
    if (!selectedUpdate || !decision) return;
    reviewMutation.mutate({ itemId: selectedUpdate.template_item_id, dec: decision, n: notes });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ArrowPathIcon className="h-8 w-8 text-orange-500" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Update Review</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Review and accept or reject new global template versions
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading...</div>
      ) : updates.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-12 text-center shadow-sm border border-gray-100 dark:border-slate-700">
          <CheckCircleIcon className="h-12 w-12 mx-auto mb-3 text-green-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">All up to date</h2>
          <p className="text-gray-500 dark:text-gray-400">No pending template updates require your review.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Updates list */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              {updates.length} pending update{updates.length !== 1 ? 's' : ''}
            </h2>
            {updates.map(u => (
              <button key={u.id} onClick={() => loadDiff(u)}
                className={`w-full text-left p-4 rounded-xl border transition-all
                  ${selectedUpdate?.id === u.id
                    ? 'border-orange-400 bg-orange-50 dark:bg-orange-900/10'
                    : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-orange-300'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm text-gray-900 dark:text-white">
                    {u.item?.name || u.template_item_id}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300">
                    v{u.pending_update_version}
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                  <span>{u.item?.item_code}</span>
                  {u.is_customized && (
                    <span className="text-purple-600 dark:text-purple-400">· customized</span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-2">
                  <DocumentMagnifyingGlassIcon className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-xs text-gray-500 dark:text-gray-400">Click to review diff</span>
                </div>
              </button>
            ))}
          </div>

          {/* Diff panel */}
          {selectedUpdate && (
            <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-slate-700 space-y-4">
              <h2 className="font-semibold text-gray-900 dark:text-white">
                {selectedUpdate.item?.name}
              </h2>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Global version {diffData?.pending_update_version || selectedUpdate.pending_update_version} available
                {diffData?.is_customized && ' · You have customized this item'}
              </div>

              {diffData && (
                <div className="grid grid-cols-1 gap-3">
                  {diffData.is_customized && (
                    <div>
                      <div className="text-xs font-medium text-purple-700 dark:text-purple-300 mb-1">Your Version</div>
                      <pre className="bg-purple-50 dark:bg-purple-900/10 rounded-lg p-3 text-xs font-mono overflow-auto max-h-40 text-purple-900 dark:text-purple-100">
                        {JSON.stringify(diffData.tenant_payload, null, 2)}
                      </pre>
                    </div>
                  )}
                  <div>
                    <div className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
                      New Global Version ({diffData.pending_update_version || diffData.global_version})
                    </div>
                    <pre className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-3 text-xs font-mono overflow-auto max-h-40 text-blue-900 dark:text-blue-100">
                      {JSON.stringify(diffData.global_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Decision */}
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Decision</div>
                <div className="flex gap-2">
                  {(['accept', 'reject', 'defer'] as const).map(d => (
                    <button key={d} onClick={() => setDecision(d)}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-all
                        ${decision === d
                          ? d === 'accept' ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                            : d === 'reject' ? 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                            : 'border-orange-400 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300'
                          : 'border-gray-300 dark:border-slate-600 text-gray-600 dark:text-gray-400 hover:border-gray-400'}`}>
                      {d === 'accept' ? <CheckCircleIcon className="h-4 w-4" />
                        : d === 'reject' ? <XCircleIcon className="h-4 w-4" />
                        : <ClockIcon className="h-4 w-4" />}
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                placeholder="Notes (optional)..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
              />

              <button onClick={handleSubmit} disabled={!decision || reviewMutation.isPending}
                className="w-full py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm font-medium">
                {reviewMutation.isPending ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
