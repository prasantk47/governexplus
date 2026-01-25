import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  RequestTypeFormConfig,
  FormFieldConfig,
  DEFAULT_REQUEST_FORM_CONFIGS,
} from '../config/requestFormConfig';
import { RequestType } from '../config/roles';

interface FormConfigContextType {
  configs: RequestTypeFormConfig[];
  getConfig: (requestType: RequestType) => RequestTypeFormConfig | undefined;
  getEnabledFields: (requestType: RequestType) => FormFieldConfig[];
  getRequiredFields: (requestType: RequestType) => FormFieldConfig[];
  isRequestTypeEnabled: (requestType: RequestType) => boolean;
  updateConfig: (requestType: RequestType, config: Partial<RequestTypeFormConfig>) => void;
  updateField: (requestType: RequestType, fieldId: string, updates: Partial<FormFieldConfig>) => void;
  saveConfigs: () => Promise<void>;
  resetToDefault: () => void;
  loading: boolean;
  hasUnsavedChanges: boolean;
}

const FormConfigContext = createContext<FormConfigContextType | undefined>(undefined);

const STORAGE_KEY = 'requestFormConfigs';

export function FormConfigProvider({ children }: { children: ReactNode }) {
  const [configs, setConfigs] = useState<RequestTypeFormConfig[]>([...DEFAULT_REQUEST_FORM_CONFIGS]);
  const [loading, setLoading] = useState(true);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Load saved configuration on mount
  useEffect(() => {
    const loadConfigs = async () => {
      try {
        // Try to load from localStorage (or API in production)
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          // Merge with defaults to handle new fields added in updates
          const merged = DEFAULT_REQUEST_FORM_CONFIGS.map((defaultConfig) => {
            const savedConfig = parsed.find(
              (c: RequestTypeFormConfig) => c.requestType === defaultConfig.requestType
            );
            if (!savedConfig) return defaultConfig;

            // Merge fields - keep saved settings but add any new default fields
            const mergedFields = defaultConfig.fields.map((defaultField) => {
              const savedField = savedConfig.fields?.find(
                (f: FormFieldConfig) => f.id === defaultField.id
              );
              return savedField ? { ...defaultField, ...savedField } : defaultField;
            });

            return {
              ...defaultConfig,
              ...savedConfig,
              fields: mergedFields,
            };
          });
          setConfigs(merged);
        }
      } catch (error) {
        console.error('Failed to load form configs:', error);
      } finally {
        setLoading(false);
      }
    };

    loadConfigs();
  }, []);

  const getConfig = (requestType: RequestType) => {
    return configs.find((c) => c.requestType === requestType);
  };

  const getEnabledFields = (requestType: RequestType) => {
    const config = getConfig(requestType);
    if (!config) return [];
    return config.fields.filter((f) => f.enabled).sort((a, b) => a.order - b.order);
  };

  const getRequiredFields = (requestType: RequestType) => {
    const config = getConfig(requestType);
    if (!config) return [];
    return config.fields
      .filter((f) => f.enabled && f.required)
      .sort((a, b) => a.order - b.order);
  };

  const isRequestTypeEnabled = (requestType: RequestType) => {
    const config = getConfig(requestType);
    return config?.enabled ?? false;
  };

  const updateConfig = (requestType: RequestType, updates: Partial<RequestTypeFormConfig>) => {
    setConfigs((prev) =>
      prev.map((config) =>
        config.requestType === requestType ? { ...config, ...updates } : config
      )
    );
    setHasUnsavedChanges(true);
  };

  const updateField = (requestType: RequestType, fieldId: string, updates: Partial<FormFieldConfig>) => {
    setConfigs((prev) =>
      prev.map((config) => {
        if (config.requestType !== requestType) return config;
        return {
          ...config,
          fields: config.fields.map((field) =>
            field.id === fieldId ? { ...field, ...updates } : field
          ),
        };
      })
    );
    setHasUnsavedChanges(true);
  };

  const saveConfigs = async () => {
    try {
      // Save to localStorage (or API in production)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(configs));
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save form configs:', error);
      throw error;
    }
  };

  const resetToDefault = () => {
    setConfigs([...DEFAULT_REQUEST_FORM_CONFIGS]);
    localStorage.removeItem(STORAGE_KEY);
    setHasUnsavedChanges(false);
  };

  return (
    <FormConfigContext.Provider
      value={{
        configs,
        getConfig,
        getEnabledFields,
        getRequiredFields,
        isRequestTypeEnabled,
        updateConfig,
        updateField,
        saveConfigs,
        resetToDefault,
        loading,
        hasUnsavedChanges,
      }}
    >
      {children}
    </FormConfigContext.Provider>
  );
}

export function useFormConfig() {
  const context = useContext(FormConfigContext);
  if (context === undefined) {
    throw new Error('useFormConfig must be used within a FormConfigProvider');
  }
  return context;
}

// Hook for getting field configuration for a specific request type
export function useRequestFormFields(requestType: RequestType) {
  const { getConfig, getEnabledFields, getRequiredFields, isRequestTypeEnabled } = useFormConfig();

  return {
    config: getConfig(requestType),
    enabledFields: getEnabledFields(requestType),
    requiredFields: getRequiredFields(requestType),
    isEnabled: isRequestTypeEnabled(requestType),
  };
}
