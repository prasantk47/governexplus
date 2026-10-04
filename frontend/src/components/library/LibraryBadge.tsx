/**
 * LibraryBadge — drop-in badge for workbench rows sourced from the Template Library.
 *
 * Usage:
 *   <LibraryBadge sourceTemplateItemId={row.source_template_item_id}
 *                 isCustomized={row.is_customized} />
 *
 * Shows nothing when sourceTemplateItemId is null/undefined (tenant-built row).
 */
import { SparklesIcon, BookOpenIcon } from '@heroicons/react/24/outline';

interface LibraryBadgeProps {
  sourceTemplateItemId?: string | null;
  isCustomized?: boolean;
  /** compact = pill only, no label (for tight table cells) */
  compact?: boolean;
}

export default function LibraryBadge({ sourceTemplateItemId, isCustomized, compact }: LibraryBadgeProps) {
  if (!sourceTemplateItemId) return null;

  if (isCustomized) {
    return (
      <span
        className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium
                   bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
        title="Customized from library template"
      >
        <SparklesIcon className="h-3 w-3" />
        {!compact && <span>Custom</span>}
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium
                 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
      title="Shipped from GovernexPlus library — updates tracked"
    >
      <BookOpenIcon className="h-3 w-3" />
      {!compact && <span>Library</span>}
    </span>
  );
}
