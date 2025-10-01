import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  FileText, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Trash2, 
  Plus,
  HardDrive,
  Clock,
  Zap
} from 'lucide-react';
import toast from 'react-hot-toast';

const UploadPage = () => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState(null);
  const [systemStats, setSystemStats] = useState({ documents: 0, loading: true });

  React.useEffect(() => {
    fetchSystemStats();
  }, []);

  const fetchSystemStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/documents');
      const data = await response.json();
      setSystemStats({
        documents: data.documents?.length || 0,
        loading: false
      });
    } catch (error) {
      console.error('Error fetching system stats:', error);
      setSystemStats({ documents: 0, loading: false });
    }
  };

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    // Handle accepted files
    const newFiles = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'pending',
      progress: 0
    }));
    
    setFiles(prev => [...prev, ...newFiles]);

    // Handle rejected files
    rejectedFiles.forEach(({ file, errors }) => {
      errors.forEach(error => {
        if (error.code === 'file-too-large') {
          toast.error(`${file.name} is too large. Max size is 10MB.`);
        } else if (error.code === 'file-invalid-type') {
          toast.error(`${file.name} is not a PDF file.`);
        }
      });
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  const removeFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select files to upload');
      return;
    }

    setUploading(true);
    setUploadResults(null);

    try {
      const formData = new FormData();
      files.forEach(({ file }) => {
        formData.append('files', file);
      });

      // Update file statuses to uploading
      setFiles(prev => prev.map(f => ({ ...f, status: 'uploading', progress: 50 })));

      const response = await fetch('http://localhost:8000/ingest', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      
      // Update file statuses to completed
      setFiles(prev => prev.map(f => ({ ...f, status: 'completed', progress: 100 })));
      
      setUploadResults(result);
      toast.success(`Successfully processed ${result.processed_files.length} documents!`);
      
      // Refresh system stats
      fetchSystemStats();

    } catch (error) {
      console.error('Upload error:', error);
      setFiles(prev => prev.map(f => ({ ...f, status: 'error', progress: 0 })));
      toast.error('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status !== 'completed'));
    setUploadResults(null);
  };

  const getFileStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'uploading':
        return (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
        );
      default:
        return <FileText className="h-5 w-5 text-gray-400" />;
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center space-x-2 bg-blue-100 rounded-full px-4 py-2 mb-6">
            <Upload className="h-5 w-5 text-blue-600" />
            <span className="text-blue-800 font-medium">Document Upload</span>
          </div>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Upload Legal Documents
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Add PDF judgments to your database for AI-powered search and analysis
          </p>
        </motion.div>

        {/* System Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
        >
          <div className="bg-white rounded-xl p-6 shadow-md border border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <HardDrive className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {systemStats.loading ? '...' : systemStats.documents}
                </p>
                <p className="text-sm text-gray-600">Documents Stored</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md border border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">AI Ready</p>
                <p className="text-sm text-gray-600">System Status</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md border border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Clock className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {files.filter(f => f.status === 'pending' || f.status === 'uploading').length}
                </p>
                <p className="text-sm text-gray-600">Queue</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Upload Area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-2xl shadow-lg border-2 border-dashed border-gray-300 p-12 text-center mb-8 hover:border-blue-400 transition-colors"
          {...getRootProps()}
        >
          <input {...getInputProps()} />
          
          <motion.div
            animate={isDragActive ? { scale: 1.05 } : { scale: 1 }}
            transition={{ duration: 0.2 }}
          >
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Upload className="h-10 w-10 text-blue-600" />
            </div>
            
            {isDragActive ? (
              <div>
                <h3 className="text-xl font-semibold text-blue-600 mb-2">
                  Drop files here!
                </h3>
                <p className="text-gray-600">Release to upload your PDF documents</p>
              </div>
            ) : (
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Drag & drop PDF files here
                </h3>
                <p className="text-gray-600 mb-4">
                  Or click to browse your computer
                </p>
                <div className="flex items-center justify-center space-x-4 text-sm text-gray-500">
                  <span>• PDF files only</span>
                  <span>• Max 10MB per file</span>
                  <span>• Multiple files supported</span>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>

        {/* File List */}
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-white rounded-xl shadow-md border border-gray-200 mb-8"
            >
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Selected Files ({files.length})
                  </h3>
                  
                  <div className="flex space-x-2">
                    {files.some(f => f.status === 'completed') && (
                      <button
                        onClick={clearCompleted}
                        className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        Clear Completed
                      </button>
                    )}
                    
                    <button
                      onClick={() => setFiles([])}
                      className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700 border border-red-300 rounded-lg hover:bg-red-50"
                    >
                      Clear All
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="max-h-64 overflow-y-auto">
                {files.map((fileItem) => (
                  <motion.div
                    key={fileItem.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="flex items-center justify-between p-4 border-b border-gray-100 last:border-b-0"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      {getFileStatusIcon(fileItem.status)}
                      
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {fileItem.file.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatFileSize(fileItem.file.size)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {fileItem.status === 'uploading' && (
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${fileItem.progress}%` }}
                          ></div>
                        </div>
                      )}
                      
                      {fileItem.status === 'pending' && (
                        <button
                          onClick={() => removeFile(fileItem.id)}
                          className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload Button */}
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center"
          >
            <motion.button
              onClick={handleUpload}
              disabled={uploading || files.every(f => f.status === 'completed')}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200 flex items-center space-x-3 shadow-lg ${
                uploading || files.every(f => f.status === 'completed')
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-xl'
              }`}
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  <span>Processing Documents...</span>
                </>
              ) : (
                <>
                  <Upload className="h-5 w-5" />
                  <span>Upload & Process Files</span>
                </>
              )}
            </motion.button>
          </motion.div>
        )}

        {/* Upload Results */}
        <AnimatePresence>
          {uploadResults && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mt-8 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6"
            >
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
                
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-green-900 mb-2">
                    Upload Successful!
                  </h3>
                  
                  <div className="space-y-2 text-sm">
                    <p className="text-green-700">
                      <strong>Processed:</strong> {uploadResults.processed_files.length} documents
                    </p>
                    <p className="text-green-700">
                      <strong>Total chunks:</strong> {uploadResults.total_chunks} searchable segments
                    </p>
                    
                    {uploadResults.processed_files.length > 0 && (
                      <div className="mt-3">
                        <p className="text-green-700 font-medium mb-1">Successfully processed:</p>
                        <div className="bg-white/50 rounded-lg p-3 max-h-32 overflow-y-auto">
                          {uploadResults.processed_files.map((filename, index) => (
                            <div key={index} className="text-green-600 text-xs">
                              ✓ {filename}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-4 flex space-x-3">
                    <button
                      onClick={() => window.location.href = '/'}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
                    >
                      Start Searching
                    </button>
                    
                    <button
                      onClick={() => {
                        setFiles([]);
                        setUploadResults(null);
                      }}
                      className="px-4 py-2 bg-white text-green-600 border border-green-300 rounded-lg hover:bg-green-50 transition-colors text-sm font-medium"
                    >
                      Upload More Files
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Help Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-12 bg-blue-50 rounded-xl p-6 border border-blue-200"
        >
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            Tips for Better Results
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
            <div className="flex items-start space-x-2">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p>Upload high-quality PDF scans for better text extraction</p>
            </div>
            
            <div className="flex items-start space-x-2">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p>Organize files with clear, descriptive filenames</p>
            </div>
            
            <div className="flex items-start space-x-2">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p>Include various types of legal documents for comprehensive search</p>
            </div>
            
            <div className="flex items-start space-x-2">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"></div>
              <p>Processing time varies with document length and complexity</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default UploadPage;