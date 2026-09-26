/**
 * Governex+ Platform - Global Search
 * Cross-module search results with category grouping
 */
import { useState, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  MagnifyingGlassIcon,
  XMarkIcon,
  UserIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  FireIcon,
  ClipboardDocumentListIcon,
  ClockIcon,
  ChevronRightIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import { usersApi, accessRequestApi, riskApi, auditApi } from '../../services/api';
import { PageHeader, Card, Badge, RiskBadge } from '../../components/ui';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SearchCategory = 'users' | 'roles' | 'access_requests' | 'violations' | 'firefighter' | 'audit';

interface SearchResult {
  id: string;
  title: string;
  subtitle: string;
  meta?: string;
  badge?: string;
  badgeVariant?: 'success' | 'warning' | 'danger' | 'info' | 'default' | 'neutral';
  riskLevel?: string;
  href: string;
  category: SearchCategory;
}

interface CategoryConfig {
  key: SearchCategory;
  label: string;
  icon: typeof UserIcon;
  color: string;
  bgColor: string;
}

const CATEGORIES: CategoryConfig[] = [
  { key: 'users', label: 'Users', icon: UserIcon, color: 'text-blue-600', bgColor: 'bg-blue-50' },
  { key: 'roles', label: 'Roles', icon: ShieldCheckIcon, color: 'text-purple-600', bgColor: 'bg-purple-50' },
  { key: 'access_requests', label: 'Access Requests', icon: DocumentTextIcon, color: 'text-amber-600', bgColor: 'bg-amber-50' },
  { key: 'violations', label: 'Violations', icon: ExclamationTriangleIcon, color: 'text-red-600', bgColor: 'bg-red-50' },
  { key: 'firefighter', label: 'Privileged Access Sessions', icon: FireIcon, color: 'text-orange-600', bgColor: 'bg-orange-50' },
  { key: 'audit', label: 'Audit Logs', icon: ClipboardDocumentListIcon, color: 'text-gray-600', bgColor: 'bg-gray-50' },
];


const RECENT_SEARCHES_KEY = 'gnx_recent_searches';
const MAX_RECENT = 8;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveRecentSearch(term: string) {
  if (!term.trim()) return;
  const prev = getRecentSearches().filter((s) => s !== term);
  const next = [term, ...prev].slice(0, MAX_RECENT);
  try {
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  } catch {
    // storage unavailable
  }
}

function removeRecentSearch(term: string) {
  const next = getRecentSearches().filter((s) => s !== term);
  try {
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
  } catch {
    // storage unavailable
  }
}


// ---------------------------------------------------------------------------
// API search — parallel calls, graceful fallback to mock
// ---------------------------------------------------------------------------

async function runSearch(query: string): Promise<SearchResult[]> {
  if (!query.trim()) return [];

  const results: SearchResult[] = [];
  const params = { search: query, limit: 10 };

  const settle = <T,>(p: Promise<T>): Promise<T | null> =>
    p.catch(() => null);

  const [usersRes, requestsRes, violationsRes, auditRes] = await Promise.all([
    settle(usersApi.list(params)),
    settle(accessRequestApi.list({ ...params, page: 1 })),
    settle(riskApi.listViolations(params)),
    settle(auditApi.getLogs({ ...params, limit: 5 })),
  ]);

  // Users
  const usersData = (usersRes as any)?.data?.users || (usersRes as any)?.data || [];
  for (const u of (Array.isArray(usersData) ? usersData : [])) {
    results.push({
      id: u.user_id || u.id,
      title: u.full_name || u.username,
      subtitle: `${u.department || 'No Dept'} — ${u.title || u.user_type || 'User'}`,
      meta: u.risk_score != null ? `Risk: ${u.risk_score}` : undefined,
      badge: u.status,
      badgeVariant: u.status === 'active' ? 'success' : u.status === 'suspended' ? 'warning' : 'neutral',
      riskLevel: u.risk_level,
      href: `/users/${u.user_id || u.id}`,
      category: 'users',
    });
  }

  // Access Requests
  const reqData = (requestsRes as any)?.data?.requests || (requestsRes as any)?.data || [];
  for (const r of (Array.isArray(reqData) ? reqData : [])) {
    results.push({
      id: r.id || r.request_id,
      title: r.id || r.request_id,
      subtitle: `${r.requester || r.requester_name || r.user || 'Unknown'} — ${r.role || r.role_id || ''}`,
      meta: r.created_at || r.request_date || r.submitted_at,
      badge: r.status,
      badgeVariant:
        r.status === 'approved' ? 'success' :
        r.status === 'pending' ? 'warning' :
        r.status === 'rejected' ? 'danger' : 'info',
      href: `/access-requests/${r.id || r.request_id}`,
      category: 'access_requests',
    });
  }

  // Violations
  const violData = (violationsRes as any)?.data?.violations || (violationsRes as any)?.data || [];
  for (const v of (Array.isArray(violData) ? violData : [])) {
    results.push({
      id: v.id,
      title: v.id,
      subtitle: `${v.user || v.user_id || ''} — ${v.rule || v.type || ''}`,
      meta: v.detected_date || v.detectedDate,
      riskLevel: v.riskLevel || v.risk_level,
      badge: v.status,
      badgeVariant: v.status === 'open' ? 'danger' : v.status === 'mitigated' ? 'success' : 'info',
      href: '/risk/violations',
      category: 'violations',
    });
  }

  // Audit
  const auditData = (auditRes as any)?.data?.logs || (auditRes as any)?.data || [];
  for (const a of (Array.isArray(auditData) ? auditData : [])) {
    results.push({
      id: a.id,
      title: a.action || a.message?.slice(0, 60) || 'Audit Event',
      subtitle: a.message || a.details || '',
      meta: a.timestamp || a.created_at,
      href: '/audit',
      category: 'audit',
    });
  }

  return results;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CategoryIcon({ category, className = '' }: { category: SearchCategory; className?: string }) {
  const conf = CATEGORIES.find((c) => c.key === category);
  if (!conf) return null;
  const Icon = conf.icon;
  return <Icon className={`${className} ${conf.color}`} />;
}

function ResultRow({ result, onClick }: { result: SearchResult; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/60 rounded-xl transition-all duration-150 text-left group"
    >
      <div className={`flex-shrink-0 h-9 w-9 rounded-lg flex items-center justify-center ${CATEGORIES.find(c => c.key === result.category)?.bgColor || 'bg-gray-50'}`}>
        <CategoryIcon category={result.category} className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-gray-900 truncate">{result.title}</span>
          {result.riskLevel && <RiskBadge level={result.riskLevel} />}
          {result.badge && !result.riskLevel && (
            <Badge variant={result.badgeVariant || 'default'} size="sm">{result.badge}</Badge>
          )}
        </div>
        <p className="text-xs text-gray-500 truncate mt-0.5">{result.subtitle}</p>
        {result.meta && <p className="text-[10px] text-gray-400 mt-0.5">{result.meta}</p>}
      </div>

      <ChevronRightIcon className="h-4 w-4 text-gray-300 group-hover:text-gray-500 flex-shrink-0 transition-colors" />
    </button>
  );
}

function CategorySection({
  config,
  results,
  onNavigate,
}: {
  config: CategoryConfig;
  results: SearchResult[];
  onNavigate: (href: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const Icon = config.icon;

  return (
    <div>
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-2.5 px-2 py-2 text-left mb-1 rounded-lg hover:bg-white/40 transition-colors"
      >
        <div className={`h-7 w-7 rounded-lg flex items-center justify-center ${config.bgColor}`}>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
        <span className="text-sm font-semibold text-gray-800">{config.label}</span>
        <span className={`ml-1 px-2 py-0.5 rounded-full text-[10px] font-bold text-white ${config.color.replace('text-', 'bg-').replace('-600', '-500')}`}>
          {results.length}
        </span>
        <ChevronRightIcon
          className={`h-4 w-4 text-gray-400 ml-auto transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {expanded && (
        <div className="space-y-0.5">
          {results.map((result) => (
            <ResultRow
              key={result.id}
              result={result}
              onClick={() => onNavigate(result.href)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SearchSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-7 w-7 rounded-lg bg-gray-200" />
            <div className="h-4 w-24 bg-gray-200 rounded" />
            <div className="h-4 w-6 bg-gray-100 rounded-full ml-2" />
          </div>
          {Array.from({ length: 3 }).map((_, j) => (
            <div key={j} className="flex items-center gap-3 px-4 py-3">
              <div className="h-9 w-9 rounded-lg bg-gray-100 flex-shrink-0" />
              <div className="flex-1">
                <div className="h-3.5 bg-gray-200 rounded w-48 mb-1.5" />
                <div className="h-3 bg-gray-100 rounded w-64" />
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GlobalSearch() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);

  const initialQuery = searchParams.get('q') || '';
  const [inputValue, setInputValue] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [activeCategory, setActiveCategory] = useState<SearchCategory | 'all'>('all');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>(getRecentSearches);

  const { data: results, isLoading, isFetching } = useQuery<SearchResult[]>({
    queryKey: ['global-search', activeQuery],
    queryFn: () => runSearch(activeQuery),
    enabled: activeQuery.trim().length >= 2,
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });

  const allResults = results || [];

  // Group by category
  const grouped = CATEGORIES.reduce<Record<SearchCategory, SearchResult[]>>(
    (acc, cat) => {
      acc[cat.key] = allResults.filter((r) => r.category === cat.key);
      return acc;
    },
    {} as Record<SearchCategory, SearchResult[]>
  );

  const visibleCategories = CATEGORIES.filter(
    (c) => grouped[c.key].length > 0 && (activeCategory === 'all' || activeCategory === c.key)
  );

  const totalResults = allResults.length;

  const commit = useCallback(
    (term: string) => {
      const trimmed = term.trim();
      if (!trimmed) return;
      setActiveQuery(trimmed);
      setShowSuggestions(false);
      saveRecentSearch(trimmed);
      setRecentSearches(getRecentSearches());
      setSearchParams({ q: trimmed }, { replace: true });
    },
    [setSearchParams]
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') commit(inputValue);
    if (e.key === 'Escape') {
      setShowSuggestions(false);
      inputRef.current?.blur();
    }
  }

  function handleNavigate(href: string) {
    navigate(href);
  }

  function clearSearch() {
    setInputValue('');
    setActiveQuery('');
    setSearchParams({}, { replace: true });
    inputRef.current?.focus();
  }

  // Autocomplete suggestions: recent searches + live suggestions from results
  const suggestions = [
    ...recentSearches.filter((s) => s.toLowerCase().includes(inputValue.toLowerCase()) && s !== inputValue),
  ].slice(0, 6);

  const noResults = activeQuery.trim().length >= 2 && !isLoading && !isFetching && allResults.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Global Search"
        subtitle="Search across users, roles, requests, violations, and audit logs"
      />

      {/* Search input */}
      <Card padding="lg">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowSuggestions(true);
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            placeholder="Search users, roles, requests, violations..."
            className="w-full pl-12 pr-28 py-4 text-base rounded-xl bg-white/50 border border-white/40 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-400 placeholder-gray-400 transition-all"
            autoFocus
          />
          <div className="absolute inset-y-0 right-0 flex items-center gap-2 pr-3">
            {(isLoading || isFetching) && activeQuery && (
              <svg className="animate-spin h-4 w-4 text-gray-400" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {inputValue && (
              <button onClick={clearSearch} className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                <XMarkIcon className="h-5 w-5" />
              </button>
            )}
            <button
              onClick={() => commit(inputValue)}
              className="px-3 py-1.5 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Search
            </button>
          </div>

          {/* Autocomplete dropdown */}
          {showSuggestions && (inputValue || recentSearches.length > 0) && (
            <div className="absolute top-full left-0 right-0 mt-2 glass-card rounded-xl shadow-glass-hover z-30 overflow-hidden">
              {recentSearches.length > 0 && !inputValue && (
                <div className="px-4 pt-3 pb-1">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recent Searches</p>
                    <button
                      onClick={() => {
                        localStorage.removeItem(RECENT_SEARCHES_KEY);
                        setRecentSearches([]);
                      }}
                      className="text-xs text-gray-400 hover:text-gray-600"
                    >
                      Clear all
                    </button>
                  </div>
                  {recentSearches.map((s) => (
                    <div key={s} className="flex items-center gap-2 py-1.5 hover:bg-white/40 rounded-lg px-2 group">
                      <ClockIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                      <button
                        className="flex-1 text-sm text-gray-700 text-left"
                        onMouseDown={() => {
                          setInputValue(s);
                          commit(s);
                        }}
                      >
                        {s}
                      </button>
                      <button
                        onMouseDown={() => {
                          removeRecentSearch(s);
                          setRecentSearches(getRecentSearches());
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <XMarkIcon className="h-3 w-3 text-gray-400 hover:text-gray-600" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {suggestions.length > 0 && inputValue && (
                <div className="px-4 py-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Suggestions</p>
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      className="w-full flex items-center gap-2 py-1.5 px-2 text-sm text-gray-700 hover:bg-white/40 rounded-lg text-left"
                      onMouseDown={() => {
                        setInputValue(s);
                        commit(s);
                      }}
                    >
                      <ArrowTrendingUpIcon className="h-3.5 w-3.5 text-gray-400" />
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {inputValue.trim().length >= 2 && (
                <div className="border-t border-white/20 px-4 py-2">
                  <button
                    onMouseDown={() => commit(inputValue)}
                    className="w-full flex items-center gap-2 py-1.5 text-sm text-primary-600 font-medium hover:text-primary-800"
                  >
                    <MagnifyingGlassIcon className="h-4 w-4" />
                    Search for &ldquo;{inputValue}&rdquo;
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Category filter tabs */}
        {activeQuery && (
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={() => setActiveCategory('all')}
              className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${
                activeCategory === 'all'
                  ? 'bg-gray-900 text-white border-gray-900'
                  : 'bg-white/40 text-gray-600 border-white/40 hover:bg-white/60'
              }`}
            >
              All Results
              {totalResults > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-white/20 text-[10px]">
                  {totalResults}
                </span>
              )}
            </button>
            {CATEGORIES.map((cat) => {
              const count = grouped[cat.key].length;
              if (!isLoading && count === 0) return null;
              const Icon = cat.icon;
              return (
                <button
                  key={cat.key}
                  onClick={() => setActiveCategory(cat.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full border transition-all ${
                    activeCategory === cat.key
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white/40 text-gray-600 border-white/40 hover:bg-white/60'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {cat.label}
                  {count > 0 && (
                    <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-white/20 text-[10px]">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </Card>

      {/* Empty state before search */}
      {!activeQuery && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            return (
              <Card
                key={cat.key}
                hover
                padding="md"
                className="cursor-pointer text-center"
                onClick={() => {
                  setActiveCategory(cat.key);
                  inputRef.current?.focus();
                }}
              >
                <div className={`h-10 w-10 rounded-xl ${cat.bgColor} flex items-center justify-center mx-auto mb-2`}>
                  <Icon className={`h-5 w-5 ${cat.color}`} />
                </div>
                <p className="text-xs font-semibold text-gray-700">{cat.label}</p>
              </Card>
            );
          })}
        </div>
      )}

      {/* Loading */}
      {(isLoading || isFetching) && activeQuery && (
        <Card padding="lg">
          <SearchSkeleton />
        </Card>
      )}

      {/* No results */}
      {noResults && (
        <Card padding="lg" className="text-center py-12">
          <MagnifyingGlassIcon className="h-12 w-12 text-gray-200 mx-auto mb-3" />
          <p className="text-base font-semibold text-gray-500">No results found</p>
          <p className="text-sm text-gray-400 mt-1">
            No matches for &ldquo;{activeQuery}&rdquo;. Try a different term.
          </p>
        </Card>
      )}

      {/* Results */}
      {!isLoading && !isFetching && allResults.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3 px-1">
            <p className="text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{totalResults}</span> result{totalResults !== 1 ? 's' : ''} for &ldquo;
              <span className="font-semibold text-gray-900">{activeQuery}</span>&rdquo;
            </p>
          </div>

          <Card padding="lg">
            <div className="space-y-6">
              {visibleCategories.map((cat) => (
                <CategorySection
                  key={cat.key}
                  config={cat}
                  results={grouped[cat.key]}
                  onNavigate={handleNavigate}
                />
              ))}

              {visibleCategories.length === 0 && activeCategory !== 'all' && (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-400">No {CATEGORIES.find(c => c.key === activeCategory)?.label} results</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Recent searches panel (shown when no query) */}
      {!activeQuery && recentSearches.length > 0 && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ClockIcon className="h-4 w-4 text-gray-500" />
              <h3 className="text-sm font-semibold text-gray-900">Recent Searches</h3>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem(RECENT_SEARCHES_KEY);
                setRecentSearches([]);
              }}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            >
              Clear all
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setInputValue(s);
                  commit(s);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 rounded-full border border-white/40 bg-white/40 hover:bg-white/70 transition-all"
              >
                <ClockIcon className="h-3.5 w-3.5 text-gray-400" />
                {s}
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeRecentSearch(s);
                    setRecentSearches(getRecentSearches());
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.click()}
                  className="ml-1 text-gray-300 hover:text-gray-600"
                >
                  <XMarkIcon className="h-3 w-3" />
                </span>
              </button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
