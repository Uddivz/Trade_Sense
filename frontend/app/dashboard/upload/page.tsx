'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { portfolioApi } from '@/lib/api';
import { usePortfolioStore } from '@/store/portfolioStore';

export default function UploadPage() {
  const router = useRouter();
  const { activePortfolio, setActivePortfolio } = usePortfolioStore();
  
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize a portfolio if none is active
  useEffect(() => {
    const initPortfolio = async () => {
      try {
        const res = await portfolioApi.list();
        if (res.data && res.data.length > 0) {
          if (!activePortfolio) {
            setActivePortfolio(res.data[0]);
          }
        } else {
          // Create default portfolio
          const createRes = await portfolioApi.create('Default Portfolio', 'Zerodha');
          setActivePortfolio(createRes.data);
        }
      } catch (err: any) {
        console.error('Failed to init portfolio', err);
      }
    };
    initPortfolio();
  }, [activePortfolio, setActivePortfolio]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelection = (selectedFile: File) => {
    setError('');
    setSuccess('');
    if (!selectedFile.name.endsWith('.csv')) {
      setError('Please upload a valid CSV file.');
      return;
    }
    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file || !activePortfolio) return;
    
    setIsUploading(true);
    setError('');
    
    try {
      const res = await portfolioApi.uploadCsv(activePortfolio.id, file);
      setSuccess(`Success! Inserted ${res.data.records_inserted} new trades.`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload CSV.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto mt-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">Upload Trade History</h1>
        <p className="text-gray-400 mt-2">
          Upload your trade book CSV from Zerodha or Groww to generate behavioral insights.
        </p>
      </div>

      <div 
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all ${
          isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 bg-gray-900/50 hover:bg-gray-800'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="text-6xl mb-4">📤</div>
        <h3 className="text-xl font-semibold text-white mb-2">Drag and drop your CSV</h3>
        <p className="text-gray-400 mb-6">or click to browse from your computer</p>
        
        <input 
          type="file" 
          ref={fileInputRef}
          className="hidden" 
          accept=".csv"
          onChange={(e) => e.target.files && handleFileSelection(e.target.files[0])}
        />
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors border border-gray-700"
        >
          Select File
        </button>
      </div>

      {file && (
        <div className="mt-8 bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="text-3xl">📄</div>
            <div>
              <div className="font-medium text-white">{file.name}</div>
              <div className="text-sm text-gray-400">{(file.size / 1024).toFixed(2)} KB</div>
            </div>
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            <button 
              onClick={() => setFile(null)}
              className="flex-1 md:flex-none px-4 py-2 border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-800 transition-colors"
              disabled={isUploading}
            >
              Cancel
            </button>
            <button 
              onClick={handleUpload}
              disabled={isUploading || !activePortfolio}
              className="flex-1 md:flex-none px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {isUploading ? 'Uploading & Analyzing...' : 'Process Analytics'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg">
          {error}
        </div>
      )}

      {success && (
        <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 text-green-400 rounded-lg">
          {success}
        </div>
      )}
    </div>
  );
}
