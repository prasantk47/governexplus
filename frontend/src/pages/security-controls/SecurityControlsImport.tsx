import { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  ArrowLeftIcon,
  ArrowUpTrayIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { securityControlsApi } from '../../services/api';

export function SecurityControlsImport() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importMethod, setImportMethod] = useState<'file' | 'paste'>('file');
  const [pasteContent, setPasteContent] = useState('');
  const [format, setFormat] = useState<'csv' | 'json'>('csv');
  const [delimiter, setDelimiter] = useState('\t');
  const [updateExisting, setUpdateExisting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<any>(null);

  const importMutation = useMutation({
    mutationFn: async () => {
      if (importMethod === 'file' && selectedFile) {
        const response = await securityControlsApi.importControlsFile(selectedFile, updateExisting);
        return response.data;
      } else if (importMethod === 'paste' && pasteContent) {
        const response = await securityControlsApi.importControls({
          content: pasteContent,
          format,
          delimiter,
          update_existing: updateExisting,
        });
        return response.data;
      }
      throw new Error('No content to import');
    },
    onSuccess: (data) => {
      setImportResult(data);
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      // Auto-detect format from file extension
      if (file.name.endsWith('.json')) {
        setFormat('json');
      } else if (file.name.endsWith('.csv')) {
        setFormat('csv');
        setDelimiter(',');
      } else {
        setFormat('csv');
        setDelimiter('\t');
      }
    }
  };

  const handleImport = () => {
    importMutation.mutate();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link to="/security-controls" className="p-1 rounded hover:bg-gray-100">
          <ArrowLeftIcon className="h-5 w-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="page-title">Import Security Controls</h1>
          <p className="page-subtitle">
            Import controls from CSV or JSON files
          </p>
        </div>
      </div>

      {importResult ? (
        /* Import Results */
        <div className="card">
          <div className="card-header">
            <h2 className="section-title flex items-center">
              <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
              Import Complete
            </h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-green-600">{importResult.details?.imported || 0}</div>
                <div className="text-xs text-green-700">Imported</div>
              </div>
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">{importResult.details?.updated || 0}</div>
                <div className="text-xs text-blue-700">Updated</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-gray-600">{importResult.details?.skipped || 0}</div>
                <div className="text-xs text-gray-700">Skipped</div>
              </div>
            </div>

            {importResult.details?.errors && importResult.details.errors.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-red-600 mb-2">Errors</h3>
                <div className="bg-red-50 rounded-lg p-3 max-h-40 overflow-y-auto">
                  {importResult.details.errors.map((error: any, index: number) => (
                    <div key={index} className="text-xs text-red-700 mb-1">
                      {error.control_id}: {error.error}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setImportResult(null);
                  setSelectedFile(null);
                  setPasteContent('');
                }}
                className="btn-secondary"
              >
                Import More
              </button>
              <Link to="/security-controls/list" className="btn-primary">
                View Controls
              </Link>
            </div>
          </div>
        </div>
      ) : (
        /* Import Form */
        <>
          {/* Import Method Selection */}
          <div className="card">
            <div className="card-header">
              <h2 className="section-title">Import Method</h2>
            </div>
            <div className="card-body">
              <div className="flex space-x-4">
                <button
                  onClick={() => setImportMethod('file')}
                  className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                    importMethod === 'file'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <ArrowUpTrayIcon className={`h-6 w-6 mx-auto mb-2 ${
                    importMethod === 'file' ? 'text-primary-600' : 'text-gray-400'
                  }`} />
                  <div className={`text-sm font-medium ${
                    importMethod === 'file' ? 'text-primary-700' : 'text-gray-700'
                  }`}>
                    Upload File
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Upload a CSV, TSV, or JSON file
                  </div>
                </button>
                <button
                  onClick={() => setImportMethod('paste')}
                  className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                    importMethod === 'paste'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <DocumentTextIcon className={`h-6 w-6 mx-auto mb-2 ${
                    importMethod === 'paste' ? 'text-primary-600' : 'text-gray-400'
                  }`} />
                  <div className={`text-sm font-medium ${
                    importMethod === 'paste' ? 'text-primary-700' : 'text-gray-700'
                  }`}>
                    Paste Content
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Paste CSV or JSON directly
                  </div>
                </button>
              </div>
            </div>
          </div>

          {/* File Upload or Paste Area */}
          <div className="card">
            <div className="card-header">
              <h2 className="section-title">
                {importMethod === 'file' ? 'Select File' : 'Paste Content'}
              </h2>
            </div>
            <div className="card-body">
              {importMethod === 'file' ? (
                <div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept=".csv,.tsv,.json,.txt"
                    className="hidden"
                  />
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors"
                  >
                    {selectedFile ? (
                      <div>
                        <DocumentTextIcon className="h-10 w-10 mx-auto text-primary-500 mb-2" />
                        <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {(selectedFile.size / 1024).toFixed(1)} KB
                        </p>
                        <p className="text-xs text-primary-600 mt-2">Click to change file</p>
                      </div>
                    ) : (
                      <div>
                        <ArrowUpTrayIcon className="h-10 w-10 mx-auto text-gray-400 mb-2" />
                        <p className="text-sm text-gray-600">
                          Click to select a file or drag and drop
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Supports CSV, TSV, and JSON formats
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex space-x-4 mb-3">
                    <div>
                      <label className="text-xs font-medium text-gray-500">Format</label>
                      <select
                        value={format}
                        onChange={(e) => setFormat(e.target.value as 'csv' | 'json')}
                        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        <option value="csv">CSV/TSV</option>
                        <option value="json">JSON</option>
                      </select>
                    </div>
                    {format === 'csv' && (
                      <div>
                        <label className="text-xs font-medium text-gray-500">Delimiter</label>
                        <select
                          value={delimiter}
                          onChange={(e) => setDelimiter(e.target.value)}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                        >
                          <option value="\t">Tab</option>
                          <option value=",">Comma</option>
                          <option value=";">Semicolon</option>
                        </select>
                      </div>
                    )}
                  </div>
                  <textarea
                    value={pasteContent}
                    onChange={(e) => setPasteContent(e.target.value)}
                    placeholder={format === 'json'
                      ? '[\n  {\n    "control_id": "CTRL-001",\n    "control_name": "...",\n    ...\n  }\n]'
                      : 'Control\tBusiness Area\tControl Type\t...\nControl 001\tSecurity Check\t...'}
                    className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Options */}
          <div className="card">
            <div className="card-header">
              <h2 className="section-title">Import Options</h2>
            </div>
            <div className="card-body">
              <label className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={updateExisting}
                  onChange={(e) => setUpdateExisting(e.target.checked)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  Update existing controls if they already exist
                </span>
              </label>

              <div className="mt-4 p-3 bg-blue-50 rounded-lg flex items-start space-x-2">
                <InformationCircleIcon className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-blue-700">
                  <p className="font-medium">Expected CSV columns:</p>
                  <p className="mt-1">
                    Control, Business Area, Control Type, Final categorization, Control Description,
                    Purpose, Procedure, Profile Parameter, Return value in system, Risk Rating,
                    Recommendation, Comment
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Import Button */}
          <div className="flex justify-end space-x-3">
            <Link to="/security-controls" className="btn-secondary">
              Cancel
            </Link>
            <button
              onClick={handleImport}
              disabled={importMutation.isPending || (importMethod === 'file' ? !selectedFile : !pasteContent)}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {importMutation.isPending ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Importing...
                </>
              ) : (
                <>
                  <ArrowUpTrayIcon className="h-4 w-4 mr-1.5" />
                  Import Controls
                </>
              )}
            </button>
          </div>

          {importMutation.isError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
              <XCircleIcon className="h-5 w-5 text-red-500 flex-shrink-0" />
              <div className="text-sm text-red-700">
                Import failed: {(importMutation.error as Error)?.message || 'Unknown error'}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
