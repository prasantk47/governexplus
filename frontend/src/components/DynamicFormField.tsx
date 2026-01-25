/**
 * Dynamic Form Field Component
 *
 * Renders form fields based on configuration from the admin settings.
 */

import { FormFieldConfig } from '../config/requestFormConfig';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface DynamicFormFieldProps {
  field: FormFieldConfig;
  value: string | boolean | string[];
  onChange: (value: string | boolean | string[]) => void;
  error?: string;
  disabled?: boolean;
}

export function DynamicFormField({ field, value, onChange, error, disabled }: DynamicFormFieldProps) {
  const baseInputClass = `w-full border rounded-md px-3 py-2 text-sm focus:ring-primary-500 focus:border-primary-500 ${
    error ? 'border-red-300' : 'border-gray-300'
  } ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}`;

  const renderField = () => {
    switch (field.type) {
      case 'text':
      case 'email':
        return (
          <input
            type={field.type}
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={disabled}
            className={baseInputClass}
          />
        );

      case 'textarea':
        return (
          <textarea
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={disabled}
            rows={4}
            className={baseInputClass}
          />
        );

      case 'select':
        return (
          <select
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={baseInputClass}
          >
            <option value="">Select {field.label}...</option>
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        return (
          <div className="space-y-2">
            {field.options?.map((opt) => (
              <label key={opt.value} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={(value as string[])?.includes(opt.value)}
                  onChange={(e) => {
                    const currentValues = (value as string[]) || [];
                    if (e.target.checked) {
                      onChange([...currentValues, opt.value]);
                    } else {
                      onChange(currentValues.filter((v) => v !== opt.value));
                    }
                  }}
                  disabled={disabled}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">{opt.label}</span>
              </label>
            ))}
          </div>
        );

      case 'checkbox':
        return (
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={value as boolean}
              onChange={(e) => onChange(e.target.checked)}
              disabled={disabled}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
            {field.description && (
              <span className="text-sm text-gray-600">{field.description}</span>
            )}
          </div>
        );

      case 'radio':
        return (
          <div className="space-y-2">
            {field.options?.map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 p-2 border rounded-lg hover:bg-gray-50 cursor-pointer">
                <input
                  type="radio"
                  name={field.id}
                  value={opt.value}
                  checked={value === opt.value}
                  onChange={(e) => onChange(e.target.value)}
                  disabled={disabled}
                  className="h-4 w-4 text-primary-600 border-gray-300"
                />
                <span className="text-sm text-gray-700">{opt.label}</span>
              </label>
            ))}
          </div>
        );

      case 'date':
        return (
          <input
            type="date"
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={baseInputClass}
          />
        );

      case 'datetime':
        return (
          <input
            type="datetime-local"
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={baseInputClass}
          />
        );

      case 'user_search':
      case 'role_search':
      case 'system_search':
        return (
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={value as string}
              onChange={(e) => onChange(e.target.value)}
              placeholder={field.placeholder || `Search ${field.type.replace('_search', '')}...`}
              disabled={disabled}
              className={`${baseInputClass} pl-9`}
            />
          </div>
        );

      default:
        return (
          <input
            type="text"
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            disabled={disabled}
            className={baseInputClass}
          />
        );
    }
  };

  return (
    <div className="space-y-1">
      {field.type !== 'checkbox' && (
        <label className="block text-sm font-medium text-gray-700">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {renderField()}
      {field.description && field.type !== 'checkbox' && (
        <p className="text-xs text-gray-500">{field.description}</p>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

// Helper component for rendering a group of fields
interface DynamicFormGroupProps {
  fields: FormFieldConfig[];
  values: Record<string, string | boolean | string[]>;
  onChange: (fieldId: string, value: string | boolean | string[]) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
  columns?: 1 | 2;
}

export function DynamicFormGroup({
  fields,
  values,
  onChange,
  errors = {},
  disabled = false,
  columns = 2,
}: DynamicFormGroupProps) {
  const gridClass = columns === 2 ? 'grid grid-cols-1 md:grid-cols-2 gap-4' : 'space-y-4';

  return (
    <div className={gridClass}>
      {fields.map((field) => (
        <DynamicFormField
          key={field.id}
          field={field}
          value={values[field.id] ?? field.defaultValue ?? ''}
          onChange={(value) => onChange(field.id, value)}
          error={errors[field.id]}
          disabled={disabled}
        />
      ))}
    </div>
  );
}
