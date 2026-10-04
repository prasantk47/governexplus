import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowDownTrayIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { api } from '../../services/api';
import {
  Card,
  PageHeader,
  Button,
} from '../../components/ui';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Survey {
  id: string;
  survey_name: string;
  status: string;
}

interface QuestionStat {
  question_id: string;
  question_text: string;
  question_type: 'text' | 'choice' | 'rating' | 'yes_no';
  response_count: number;
  avg_rating?: number;
  choice_breakdown?: { option: string; count: number; percentage: number }[];
  text_responses?: string[];
  yes_count?: number;
  no_count?: number;
}

interface SurveyAnalytics {
  survey_id: string;
  survey_name: string;
  total_sent: number;
  total_completed: number;
  completion_rate: number;
  questions: QuestionStat[];
}

// ─── Components ───────────────────────────────────────────────────────────────

function CompletionBar({ rate, completed, total }: { rate: number; completed: number; total: number }) {
  const color = rate >= 80 ? 'bg-green-500' : rate >= 50 ? 'bg-yellow-400' : 'bg-red-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-sm">
        <span className="text-gray-700 dark:text-gray-300 font-medium">{rate}% completion</span>
        <span className="text-gray-400">{completed} / {total} responses</span>
      </div>
      <div className="h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${rate}%` }} />
      </div>
    </div>
  );
}

function ChoiceBar({ option, count, percentage, maxCount }: { option: string; count: number; percentage: number; maxCount: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-700 dark:text-gray-300 w-32 flex-shrink-0 truncate" title={option}>
        {option}
      </span>
      <div className="flex-1 h-5 bg-gray-100 dark:bg-slate-700 rounded overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded transition-all duration-500"
          style={{ width: maxCount > 0 ? `${(count / maxCount) * 100}%` : '0%' }}
        />
      </div>
      <span className="text-xs text-gray-500 w-14 flex-shrink-0 text-right">
        {count} ({percentage}%)
      </span>
    </div>
  );
}

function StarRating({ avg }: { avg: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map(n => (
          <div
            key={n}
            className={`h-6 w-6 rounded ${n <= Math.round(avg) ? 'bg-yellow-400' : 'bg-gray-200 dark:bg-slate-600'}`}
          />
        ))}
      </div>
      <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{avg.toFixed(1)}</span>
      <span className="text-sm text-gray-400">/ 5</span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ResponseAnalytics() {
  const [selectedSurveyId, setSelectedSurveyId] = useState('');

  // ── Queries ──

  const { data: surveysData } = useQuery<Survey[]>({
    queryKey: ['surveys-list'],
    queryFn: () => api.get('/surveys').then(r => r.data?.surveys ?? r.data ?? []),
  });

  const { data: analyticsData, isLoading } = useQuery<SurveyAnalytics>({
    queryKey: ['survey-analytics', selectedSurveyId],
    queryFn: () => api.get(`/surveys/${selectedSurveyId}/analytics`).then(r => r.data),
    enabled: !!selectedSurveyId,
  });

  const surveys: Survey[] = surveysData ?? [];

  function handleExport() {
    if (!selectedSurveyId) return;
    api
      .get(`/surveys/${selectedSurveyId}/export`, { responseType: 'blob' })
      .then(r => {
        const url = URL.createObjectURL(new Blob([r.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = `survey-${selectedSurveyId}-responses.csv`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => {
        // fallback: open as new tab
        window.open(`/api/surveys/${selectedSurveyId}/export`, '_blank');
      });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Response Analytics"
        subtitle="Analyze survey completion rates and response data"
        actions={
          selectedSurveyId && (
            <Button
              variant="secondary"
              icon={<ArrowDownTrayIcon className="h-4 w-4" />}
              onClick={handleExport}
            >
              Export Results
            </Button>
          )
        }
      />

      {/* Survey Selector */}
      <Card padding="md">
        <div className="flex items-center gap-4">
          <ChartBarIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Select Survey
            </label>
            <select
              value={selectedSurveyId}
              onChange={e => setSelectedSurveyId(e.target.value)}
              className="w-full text-sm border border-gray-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Choose a survey to view analytics...</option>
              {surveys.map(s => (
                <option key={s.id} value={s.id}>{s.survey_name}</option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Loading */}
      {isLoading && (
        <Card padding="md">
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center gap-3 text-gray-400">
              <div className="h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              Loading analytics...
            </div>
          </div>
        </Card>
      )}

      {/* Analytics */}
      {analyticsData && !isLoading && (
        <div className="space-y-6">
          {/* Completion Rate */}
          <Card padding="md">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
              {analyticsData.survey_name}
            </h3>
            <CompletionBar
              rate={analyticsData.completion_rate}
              completed={analyticsData.total_completed}
              total={analyticsData.total_sent}
            />
          </Card>

          {/* Per-Question Stats */}
          {analyticsData.questions.length > 0 ? (
            <div className="space-y-4">
              {analyticsData.questions.map((q, idx) => (
                <Card key={q.question_id} padding="md">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs text-gray-400 mr-2">Q{idx + 1}</span>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {q.question_text}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400 flex-shrink-0">
                        {q.response_count} response{q.response_count !== 1 ? 's' : ''}
                      </span>
                    </div>

                    {/* Choice breakdown */}
                    {q.question_type === 'choice' && (q.choice_breakdown ?? []).length > 0 && (
                      <div className="space-y-2">
                        {(q.choice_breakdown ?? []).map(opt => {
                          const maxCount = Math.max(...(q.choice_breakdown ?? []).map(o => o.count));
                          return (
                            <ChoiceBar
                              key={opt.option}
                              option={opt.option}
                              count={opt.count}
                              percentage={opt.percentage}
                              maxCount={maxCount}
                            />
                          );
                        })}
                      </div>
                    )}

                    {/* Rating */}
                    {q.question_type === 'rating' && q.avg_rating !== undefined && (
                      <StarRating avg={q.avg_rating} />
                    )}

                    {/* Yes/No */}
                    {q.question_type === 'yes_no' && q.yes_count !== undefined && (
                      <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-3 rounded-full bg-green-500" />
                          <span className="text-sm text-gray-700 dark:text-gray-300">Yes: {q.yes_count}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-3 rounded-full bg-red-500" />
                          <span className="text-sm text-gray-700 dark:text-gray-300">No: {q.no_count ?? 0}</span>
                        </div>
                        {(q.yes_count + (q.no_count ?? 0)) > 0 && (
                          <div className="flex-1 h-2 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 rounded-full"
                              style={{
                                width: `${(q.yes_count / (q.yes_count + (q.no_count ?? 0))) * 100}%`,
                              }}
                            />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Text responses */}
                    {q.question_type === 'text' && (q.text_responses ?? []).length > 0 && (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {(q.text_responses ?? []).slice(0, 8).map((resp, i) => (
                          <div
                            key={i}
                            className="bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2 text-sm text-gray-700 dark:text-gray-300 italic"
                          >
                            "{resp}"
                          </div>
                        ))}
                        {(q.text_responses ?? []).length > 8 && (
                          <p className="text-xs text-gray-400 text-center">
                            +{(q.text_responses ?? []).length - 8} more responses
                          </p>
                        )}
                      </div>
                    )}

                    {q.response_count === 0 && (
                      <p className="text-sm text-gray-400 italic">No responses yet</p>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card padding="md">
              <div className="text-center py-8 text-gray-400">
                <ChartBarIcon className="h-10 w-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No question data available for this survey</p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Empty State */}
      {!selectedSurveyId && !isLoading && (
        <Card padding="md">
          <div className="text-center py-12">
            <ChartBarIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Select a survey above to view response analytics and completion rates.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
