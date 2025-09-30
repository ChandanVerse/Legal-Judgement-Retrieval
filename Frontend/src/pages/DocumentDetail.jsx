import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Calendar, Scale, Copy } from 'lucide-react';
import toast from 'react-hot-toast';

const DocumentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        const response = await fetch(`http://localhost:8000/documents/${id}`);
        if (!response.ok) {
          throw new Error('Document not found');
        }
        const data = await response.json();
        setDocument(data);
      } catch (error) {
        console.error('Error fetching document:', error);
        toast.error('Failed to load document.');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [id]);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center text-center">
        <div>
          <h2 className="text-xl font-semibold mb-2">Document not found</h2>
          <button onClick={() => navigate(-1)} className="text-blue-600 hover:underline">
            Go back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="h-5 w-5" />
          <span>Back to Results</span>
        </button>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg shadow-md p-8"
        >
          <h1 className="text-3xl font-bold text-gray-900 mb-4">{document.metadata.filename}</h1>
          
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-6">
            <div className="flex items-center space-x-1">
              <Scale className="h-4 w-4" />
              <span>{document.metadata.court_type || 'N/A'}</span>
            </div>
            <div className="flex items-center space-x-1">
              <Calendar className="h-4 w-4" />
              <span>{document.metadata.year || 'N/A'}</span>
            </div>
          </div>

          <div className="prose max-w-none">
            <h2 className="text-xl font-semibold mb-2 capitalize">{document.metadata.section}</h2>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 whitespace-pre-wrap">
              <p>{document.content}</p>
            </div>
          </div>
          
          <div className="mt-6">
            <button
              onClick={() => copyToClipboard(document.content)}
              className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Copy className="h-4 w-4" />
              <span>Copy Content</span>
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default DocumentDetail;