import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText, Calendar, User, Scale, Copy, Download, Share2 } from 'lucide-react';
import toast from 'react-hot-toast';

const DocumentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');

  useEffect(() => {
    // In a real implementation, you would fetch document details by ID
    // For demo purposes, we'll simulate document data
    setTimeout(() => {
      setDocument({
        id: id,
        filename: `Legal_Judgment_${id}.pdf`,
        title: "Constitutional Validity of Preventive Detention Laws",
        court: "Supreme Court of India",
        date: "2023-08-15",
        judges: ["Justice A. Kumar", "Justice B. Singh", "Justice C. Patel"],
        citation: "2023 SCC 456",
        sections: {
          facts: "The petitioner challenged the constitutional validity of preventive detention laws under Article 22 of the Constitution. The case arose from the detention of several individuals without trial for extended periods...",
          grounds: "The grounds for challenge included violation of fundamental rights under Articles 14, 19, and 21 of the Constitution. The petitioner argued that preventive detention without proper safeguards violates due process...",
          judgment: "The Court held that while preventive detention is constitutionally permissible under certain circumstances, it must be subject to strict judicial review and procedural safeguards...",
          ratio: "Preventive detention laws must balance national security concerns with individual liberty rights. The detention must be based on objective satisfaction and subject to periodic review..."
        },
        metadata: {
          pages: 45,
          wordCount: 12500,
          processingDate: "2023-12-01",
          tags: ["Constitutional Law", "Fundamental Rights", "Preventive Detention"]
        }
      });
      setLoading(false);
    }, 1000);
  }, [id]);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const sections = [
    { id: 'overview', label: 'Overview' },
    { id: 'facts', label: 'Facts' },
    { id: 'grounds', label: 'Legal Grounds' },
    { id: 'judgment', label: 'Judgment' },
    { id: 'ratio', label: 'Ratio Decidendi' }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Document Not Found</h2>
          <p className="text-gray-600 mb-4">The requested document could not be found.</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8"
        >
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Results</span>
            </button>

            <div className="flex space-x-2">
              <button
                onClick={() => copyToClipboard(document.citation)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Copy className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                <Share2 className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                <Download className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <h1 className="text-3xl font-bold text-gray-900 mb-4">{document.title}</h1>
              
              <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-6">
                <div className="flex items-center space-x-1">
                  <Scale className="h-4 w-4" />
                  <span>{document.court}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Calendar className="h-4 w-4" />
                  <span>{new Date(document.date).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <FileText className="h-4 w-4" />
                  <span>{document.citation}</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-6">
                {document.metadata.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Document Info</h3>
              
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-medium text-gray-700">Judges:</span>
                  <div className="mt-1">
                    {document.judges.map((judge, index) => (
                      <div key={index} className="text-gray-600">{judge}</div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <span className="font-medium text-gray-700">Pages:</span>
                  <span className="ml-2 text-gray-600">{document.metadata.pages}</span>
                </div>
                
                <div>
                  <span className="font-medium text-gray-700">Word Count:</span>
                  <span className="ml-2 text-gray-600">{document.metadata.wordCount.toLocaleString()}</span>
                </div>
                
                <div>
                  <span className="font-medium text-gray-700">Processed:</span>
                  <span className="ml-2 text-gray-600">
                    {new Date(document.metadata.processingDate).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Navigation */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-3">Sections</h3>
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeSection === section.id
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    {section.label}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-8"
            >
              {activeSection === 'overview' ? (
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-6">Document Overview</h2>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="font-semibold text-blue-900 mb-2">Case Summary</h3>
                      <p className="text-blue-800 text-sm">
                        This landmark judgment addresses the constitutional validity of preventive detention laws,
                        balancing national security concerns with fundamental rights protection.
                      </p>
                    </div>
                    
                    <div className="bg-green-50 rounded-lg p-4">
                      <h3 className="font-semibold text-green-900 mb-2">Legal Significance</h3>
                      <p className="text-green-800 text-sm">
                        Sets important precedent for detention laws, establishing stricter judicial review
                        requirements and enhanced procedural safeguards.
                      </p>
                    </div>
                  </div>

                  <div className="prose max-w-none">
                    <h3>Key Legal Principles</h3>
                    <ul>
                      <li>Preventive detention must be subject to strict judicial scrutiny</li>
                      <li>Detention orders require objective satisfaction of authorities</li>
                      <li>Periodic review mechanisms are constitutionally mandated</li>
                      <li>Balance between individual liberty and collective security</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 capitalize">
                      {activeSection === 'ratio' ? 'Ratio Decidendi' : activeSection}
                    </h2>
                    <button
                      onClick={() => copyToClipboard(document.sections[activeSection])}
                      className="flex items-center space-x-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      <Copy className="h-4 w-4" />
                      <span>Copy</span>
                    </button>
                  </div>
                  
                  <div className="prose max-w-none">
                    <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                      <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {document.sections[activeSection]}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentDetail;