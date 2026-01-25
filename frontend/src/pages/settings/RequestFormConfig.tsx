import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  Cog6ToothIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  PlusIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  ExclamationCircleIcon,
  DocumentTextIcon,
  UserIcon,
  ShieldCheckIcon,
  ClockIcon,
  Squares2X2Icon,
} from '@heroicons/react/24/outline';
import {
  FormFieldConfig,
  FIELD_DEFINITIONS,
  FIELD_CATEGORIES,
} from '../../config/requestFormConfig';
import { REQUEST_TYPES, RequestType } from '../../config/roles';
import { useFormConfig } from '../../contexts/FormConfigContext';

const requestTypeIcons: Record<string, React.ReactNode> = {
  [REQUEST_TYPES.NEW_ACCOUNT]: <UserIcon className="h-5 w-5" />,
  [REQUEST_TYPES.CHANGE_ACCOUNT]: <Cog6ToothIcon className="h-5 w-5" />,
  [REQUEST_TYPES.COPY_USER]: <DocumentTextIcon className="h-5 w-5" />,
  [REQUEST_TYPES.REMOVE_ACCOUNT]: <TrashIcon className="h-5 w-5" />,
  [REQUEST_TYPES.LOCK_ACCOUNT]: <ShieldCheckIcon className="h-5 w-5" />,
  [REQUEST_TYPES.UNLOCK_ACCOUNT]: <ShieldCheckIcon className="h-5 w-5" />,
};

const categoryIcons: Record<string, React.ReactNode> = {
  user_info: <UserIcon className="h-4 w-4" />,
  access_details: <ShieldCheckIcon className="h-4 w-4" />,
  justification: <DocumentTextIcon className="h-4 w-4" />,
  timing: <ClockIcon className="h-4 w-4" />,
  other: <Squares2X2Icon className="h-4 w-4" />,
};

export function RequestFormConfig() {
  const {
    configs,
    getConfig,
    updateConfig,
    updateField,
    saveConfigs,
    resetToDefault,
    hasUnsavedChanges,
  } = useFormConfig();

  const [selectedRequestType, setSelectedRequestType] = useState<RequestType>(REQUEST_TYPES.NEW_ACCOUNT);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['user_info', 'access_details', 'justification', 'timing', 'other']);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  const currentConfig = getConfig(selectedRequestType);

  const toggleCategory = (category: string) => {
    if (expandedCategories.includes(category)) {
      setExpandedCategories(expandedCategories.filter((c) => c !== category));
    } else {
      setExpandedCategories([...expandedCategories, category]);
    }
  };

  const toggleFieldEnabled = (fieldId: string) => {
    const field = currentConfig?.fields.find((f) => f.id === fieldId);
    if (field) {
      updateField(selectedRequestType, fieldId, { enabled: !field.enabled });
    }
  };

  const toggleFieldRequired = (fieldId: string) => {
    const field = currentConfig?.fields.find((f) => f.id === fieldId);
    if (field) {
      updateField(selectedRequestType, fieldId, { required: !field.required });
    }
  };

  const moveField = (fieldId: string, direction: 'up' | 'down') => {
    if (!currentConfig) return;
    const fields = [...currentConfig.fields].sort((a, b) => a.order - b.order);
    const index = fields.findIndex((f) => f.id === fieldId);
    if (index === -1) return;
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === fields.length - 1) return;

    const swapIndex = direction === 'up' ? index - 1 : index + 1;
    const tempOrder = fields[index].order;

    updateField(selectedRequestType, fields[index].id, { order: fields[swapIndex].order });
    updateField(selectedRequestType, fields[swapIndex].id, { order: tempOrder });
  };

  const toggleRequestTypeEnabled = () => {
    if (currentConfig) {
      updateConfig(selectedRequestType, { enabled: !currentConfig.enabled });
    }
  };

  const addAvailableField = (fieldDef: typeof FIELD_DEFINITIONS[string]) => {
    if (!currentConfig) return;
    const existingField = currentConfig.fields.find((f) => f.id === fieldDef.id);
    if (existingField) {
      toggleFieldEnabled(fieldDef.id);
    } else {
      const maxOrder = Math.max(...currentConfig.fields.map((f) => f.order), 0);
      const newField: FormFieldConfig = {
        ...fieldDef,
        enabled: true,
        required: false,
        order: maxOrder + 1,
      };
      updateConfig(selectedRequestType, {
        fields: [...currentConfig.fields, newField],
      });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConfigs();
      toast.success('Configuration saved successfully');
    } catch (error) {
      toast.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleResetClick = () => {
    setShowResetConfirm(true);
  };

  const handleResetConfirm = () => {
    resetToDefault();
    setShowResetConfirm(false);
    toast.success('Configuration reset to defaults');
  };

  const handleResetCancel = () => {
    setShowResetConfirm(false);
  };

  // Group fields by category
  const groupedFields = currentConfig?.fields.reduce((acc, field) => {
    const category = field.category || 'other';
    if (!acc[category]) acc[category] = [];
    acc[category].push(field);
    return acc;
  }, {} as Record<string, FormFieldConfig[]>) || {};

  // Get available fields not yet added
  const availableFields = Object.values(FIELD_DEFINITIONS).filter(
    (def) => !currentConfig?.fields.find((f) => f.id === def.id)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Access Request Form Configuration</h2>
          <p className="mt-1 text-sm text-gray-500">
            Configure which fields appear on each request type form
          </p>
        </div>
        <div className="flex items-center gap-3">
          {hasUnsavedChanges && (
            <span className="text-sm text-amber-600 flex items-center">
              <ExclamationCircleIcon className="h-4 w-4 mr-1" />
              Unsaved changes
            </span>
          )}
          <button
            onClick={handleResetClick}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Reset to Default
          </button>
          <button
            onClick={handleSave}
            disabled={!hasUnsavedChanges || saving}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Request Type Selector */}
        <div className="col-span-3">
          <div className="bg-white shadow rounded-lg">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-sm font-medium text-gray-900">Request Types</h3>
            </div>
            <nav className="p-2">
              {configs.map((config) => (
                <button
                  key={config.requestType}
                  onClick={() => setSelectedRequestType(config.requestType)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-left rounded-md mb-1 ${
                    selectedRequestType === config.requestType
                      ? 'bg-primary-50 text-primary-700 border border-primary-200'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={selectedRequestType === config.requestType ? 'text-primary-600' : 'text-gray-400'}>
                      {requestTypeIcons[config.requestType]}
                    </span>
                    <span className="text-sm font-medium">{config.displayName}</span>
                  </div>
                  {!config.enabled && (
                    <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                      Disabled
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Preview Toggle */}
          <div className="mt-4 bg-white shadow rounded-lg p-4">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="w-full flex items-center justify-between text-sm font-medium text-gray-700"
            >
              <span className="flex items-center gap-2">
                {showPreview ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </span>
            </button>
          </div>
        </div>

        {/* Field Configuration */}
        <div className="col-span-9">
          {currentConfig && (
            <div className="space-y-4">
              {/* Request Type Header */}
              <div className="bg-white shadow rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary-100 rounded-lg text-primary-600">
                      {requestTypeIcons[currentConfig.requestType]}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{currentConfig.displayName}</h3>
                      <p className="text-sm text-gray-500">{currentConfig.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-sm text-gray-500">
                      {currentConfig.fields.filter((f) => f.enabled).length} of {currentConfig.fields.length} fields enabled
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <span className="text-sm text-gray-700">Enable Request Type</span>
                      <button
                        onClick={toggleRequestTypeEnabled}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          currentConfig.enabled ? 'bg-primary-600' : 'bg-gray-200'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            currentConfig.enabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </label>
                  </div>
                </div>
              </div>

              {/* Fields by Category */}
              {Object.entries(FIELD_CATEGORIES).map(([categoryKey, categoryInfo]) => {
                const categoryFields = groupedFields[categoryKey] || [];
                if (categoryFields.length === 0) return null;
                const isExpanded = expandedCategories.includes(categoryKey);

                return (
                  <div key={categoryKey} className="bg-white shadow rounded-lg overflow-hidden">
                    <button
                      onClick={() => toggleCategory(categoryKey)}
                      className="w-full p-4 border-b border-gray-200 flex items-center justify-between hover:bg-gray-50"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-gray-400">{categoryIcons[categoryKey]}</span>
                        <div className="text-left">
                          <h4 className="text-sm font-medium text-gray-900">{categoryInfo.label}</h4>
                          <p className="text-xs text-gray-500">{categoryInfo.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500">
                          {categoryFields.filter((f) => f.enabled).length} / {categoryFields.length} enabled
                        </span>
                        {isExpanded ? (
                          <ChevronUpIcon className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                        )}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="divide-y divide-gray-100">
                        {categoryFields
                          .sort((a, b) => a.order - b.order)
                          .map((field, index) => (
                            <div
                              key={field.id}
                              className={`p-4 flex items-center justify-between ${
                                !field.enabled ? 'bg-gray-50 opacity-60' : ''
                              }`}
                            >
                              <div className="flex items-center gap-4">
                                {/* Reorder buttons */}
                                <div className="flex flex-col gap-1">
                                  <button
                                    onClick={() => moveField(field.id, 'up')}
                                    disabled={index === 0}
                                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                                  >
                                    <ChevronUpIcon className="h-3 w-3" />
                                  </button>
                                  <button
                                    onClick={() => moveField(field.id, 'down')}
                                    disabled={index === categoryFields.length - 1}
                                    className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                                  >
                                    <ChevronDownIcon className="h-3 w-3" />
                                  </button>
                                </div>

                                {/* Field info */}
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium text-gray-900">{field.label}</span>
                                    <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                                      {field.type}
                                    </span>
                                    {field.required && field.enabled && (
                                      <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded">
                                        Required
                                      </span>
                                    )}
                                  </div>
                                  {field.description && (
                                    <p className="text-xs text-gray-500 mt-0.5">{field.description}</p>
                                  )}
                                </div>
                              </div>

                              {/* Controls */}
                              <div className="flex items-center gap-4">
                                {/* Required toggle */}
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <span className="text-xs text-gray-500">Required</span>
                                  <button
                                    onClick={() => toggleFieldRequired(field.id)}
                                    disabled={!field.enabled}
                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                                      field.required && field.enabled ? 'bg-red-500' : 'bg-gray-200'
                                    } ${!field.enabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                                  >
                                    <span
                                      className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                                        field.required ? 'translate-x-5' : 'translate-x-1'
                                      }`}
                                    />
                                  </button>
                                </label>

                                {/* Enabled toggle */}
                                <label className="flex items-center gap-2 cursor-pointer">
                                  <span className="text-xs text-gray-500">Enabled</span>
                                  <button
                                    onClick={() => toggleFieldEnabled(field.id)}
                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                                      field.enabled ? 'bg-green-500' : 'bg-gray-200'
                                    }`}
                                  >
                                    <span
                                      className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                                        field.enabled ? 'translate-x-5' : 'translate-x-1'
                                      }`}
                                    />
                                  </button>
                                </label>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Add Available Fields */}
              {availableFields.length > 0 && (
                <div className="bg-white shadow rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Add More Fields</h4>
                  <div className="flex flex-wrap gap-2">
                    {availableFields.map((fieldDef) => (
                      <button
                        key={fieldDef.id}
                        onClick={() => addAvailableField(fieldDef)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-full hover:bg-gray-200"
                      >
                        <PlusIcon className="h-3 w-3" />
                        {fieldDef.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Preview Panel */}
      {showPreview && currentConfig && (
        <div className="bg-white shadow rounded-lg">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-900">Form Preview - {currentConfig.displayName}</h3>
            <p className="text-xs text-gray-500 mt-1">This is how the form will appear to users</p>
          </div>
          <div className="p-6">
            <div className="max-w-2xl mx-auto space-y-4">
              {currentConfig.fields
                .filter((f) => f.enabled)
                .sort((a, b) => a.order - b.order)
                .map((field) => (
                  <div key={field.id}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    {field.type === 'textarea' ? (
                      <textarea
                        placeholder={field.placeholder}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm bg-gray-50"
                        rows={3}
                        disabled
                      />
                    ) : field.type === 'select' ? (
                      <select
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm bg-gray-50"
                        disabled
                      >
                        <option>Select {field.label}...</option>
                        {field.options?.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : field.type === 'checkbox' ? (
                      <div className="flex items-center gap-2">
                        <input type="checkbox" disabled className="h-4 w-4 rounded border-gray-300" />
                        <span className="text-sm text-gray-600">{field.description}</span>
                      </div>
                    ) : field.type === 'radio' ? (
                      <div className="space-y-2">
                        {field.options?.map((opt) => (
                          <label key={opt.value} className="flex items-center gap-2">
                            <input type="radio" name={field.id} disabled className="h-4 w-4 border-gray-300" />
                            <span className="text-sm text-gray-600">{opt.label}</span>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <input
                        type={field.type === 'email' ? 'email' : field.type === 'date' ? 'date' : 'text'}
                        placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}...`}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm bg-gray-50"
                        disabled
                      />
                    )}
                    {field.description && field.type !== 'checkbox' && (
                      <p className="mt-1 text-xs text-gray-500">{field.description}</p>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 rounded-full">
                <ExclamationCircleIcon className="h-6 w-6 text-amber-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Reset Configuration</h3>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to reset all form configurations to their default settings?
              This will remove all customizations and cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={handleResetCancel}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleResetConfirm}
                className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700"
              >
                Reset to Defaults
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
