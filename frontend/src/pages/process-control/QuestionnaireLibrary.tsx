import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { QuestionMarkCircleIcon, DocumentTextIcon, PlusIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { PageHeader, Card } from '../../components/ui';
import { StatCard } from '../../components/StatCard';
import api from '../../services/api';

interface Question {
  question_id: string;
  text: string;
  question_type: string;
  category?: string;
  framework_ref?: string;
  options?: string[];
  is_required: boolean;
  is_active: boolean;
  created_at: string;
}

interface Questionnaire {
  questionnaire_id: string;
  title: string;
  questionnaire_type: string;
  description?: string;
  status: string;
  question_count: number;
  created_at: string;
}

const typeColors: Record<string, string> = {
  yes_no: 'bg-blue-100 text-blue-700',
  multiple_choice: 'bg-purple-100 text-purple-700',
  rating: 'bg-yellow-100 text-yellow-800',
  text: 'bg-gray-100 text-gray-600',
  numeric: 'bg-green-100 text-green-700',
};

export function QuestionnaireLibrary() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'questions' | 'questionnaires'>('questions');
  const [showCreateQ, setShowCreateQ] = useState(false);
  const [showCreateQnr, setShowCreateQnr] = useState(false);

  const [qForm, setQForm] = useState({
    text: '', question_type: 'yes_no', category: 'general',
    framework_ref: '', is_required: true,
  });
  const [qnrForm, setQnrForm] = useState({
    title: '', questionnaire_type: 'csa', description: '',
  });

  const { data: questionsData, isLoading: qLoading } = useQuery({
    queryKey: ['question-library'],
    queryFn: () => api.get('/process-control/question-library').then(r => r.data),
    refetchInterval: 60000,
  });

  const { data: questionnairesData, isLoading: qnrLoading } = useQuery({
    queryKey: ['questionnaires'],
    queryFn: () => api.get('/process-control/questionnaires').then(r => r.data),
    refetchInterval: 60000,
  });

  const createQMut = useMutation({
    mutationFn: (body: any) => api.post('/process-control/question-library', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['question-library'] }); setShowCreateQ(false); },
  });

  const createQnrMut = useMutation({
    mutationFn: (body: any) => api.post('/process-control/questionnaires', body).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['questionnaires'] }); setShowCreateQnr(false); },
  });

  const questions: Question[] = questionsData?.questions || [];
  const questionnaires: Questionnaire[] = questionnairesData?.questionnaires || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Question Library"
        subtitle="Reusable assessment questions and assembled questionnaires"
        actions={
          <div className="flex gap-2">
            <button onClick={() => setShowCreateQ(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-white border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
              <PlusIcon className="h-4 w-4" /> Add Question
            </button>
            <button onClick={() => setShowCreateQnr(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
              <PlusIcon className="h-4 w-4" /> New Questionnaire
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard title="Library Questions" value={questions.length || '—'} icon={QuestionMarkCircleIcon} iconBgColor="stat-icon-blue" iconColor="" />
        <StatCard title="Questionnaires" value={questionnaires.length || '—'} icon={DocumentTextIcon} iconBgColor="stat-icon-purple" iconColor="" />
        <StatCard title="Active" value={questionnaires.filter(q => q.status === 'active').length || '—'} icon={CheckCircleIcon} iconBgColor="stat-icon-green" iconColor="" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {(['questions', 'questionnaires'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'questions' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Question Library</h2>
          {qLoading ? (
            <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
          ) : questions.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No questions in library</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    {['Question', 'Type', 'Category', 'Framework', 'Required'].map(h => (
                      <th key={h} className="pb-2 text-left text-xs font-semibold text-gray-500 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {questions.map(q => (
                    <tr key={q.question_id}>
                      <td className="py-2 pr-4 max-w-sm">
                        <div className="text-xs font-medium text-gray-900 truncate">{q.text}</div>
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[q.question_type] || 'bg-gray-100 text-gray-600'}`}>
                          {q.question_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-xs text-gray-600 capitalize">{q.category || '—'}</td>
                      <td className="py-2 pr-4 text-xs text-gray-500">{q.framework_ref || '—'}</td>
                      <td className="py-2 pr-4">
                        <span className={`text-xs font-medium ${q.is_required ? 'text-red-600' : 'text-gray-400'}`}>
                          {q.is_required ? 'Yes' : 'No'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'questionnaires' && (
        <Card>
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Assembled Questionnaires</h2>
          {qnrLoading ? (
            <div className="text-xs text-gray-400 text-center py-8">Loading...</div>
          ) : questionnaires.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-8">No questionnaires assembled</div>
          ) : (
            <div className="space-y-3">
              {questionnaires.map(qnr => (
                <div key={qnr.questionnaire_id} className="flex items-center justify-between p-3 border border-gray-100 rounded-xl hover:bg-gray-50">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{qnr.title}</div>
                    {qnr.description && <div className="text-xs text-gray-400">{qnr.description}</div>}
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500 capitalize">{qnr.questionnaire_type.replace(/_/g, ' ')}</span>
                      <span className="text-xs text-gray-300">·</span>
                      <span className="text-xs text-gray-500">{qnr.question_count} questions</span>
                    </div>
                  </div>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${qnr.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {qnr.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Create Question Modal */}
      {showCreateQ && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Add Question to Library</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Question Text *</label>
                <textarea value={qForm.text} onChange={e => setQForm(f => ({ ...f, text: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                  <select value={qForm.question_type} onChange={e => setQForm(f => ({ ...f, question_type: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    {['yes_no', 'multiple_choice', 'rating', 'text', 'numeric'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
                  <input value={qForm.category} onChange={e => setQForm(f => ({ ...f, category: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Framework Ref</label>
                <input value={qForm.framework_ref} onChange={e => setQForm(f => ({ ...f, framework_ref: e.target.value }))}
                  placeholder="e.g. SOC 2 CC6.1" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createQMut.mutate(qForm)}
                disabled={createQMut.isPending || !qForm.text}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createQMut.isPending ? 'Adding…' : 'Add Question'}
              </button>
              <button onClick={() => setShowCreateQ(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create Questionnaire Modal */}
      {showCreateQnr && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Create Questionnaire</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title *</label>
                <input value={qnrForm.title} onChange={e => setQnrForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                <select value={qnrForm.questionnaire_type} onChange={e => setQnrForm(f => ({ ...f, questionnaire_type: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {['csa', 'tprm', 'audit', 'risk_assessment', 'compliance'].map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={qnrForm.description} onChange={e => setQnrForm(f => ({ ...f, description: e.target.value }))}
                  rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button onClick={() => createQnrMut.mutate(qnrForm)}
                disabled={createQnrMut.isPending || !qnrForm.title}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
                {createQnrMut.isPending ? 'Creating…' : 'Create Questionnaire'}
              </button>
              <button onClick={() => setShowCreateQnr(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-xl py-2 text-sm font-semibold hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
