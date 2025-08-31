import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, FileText, Star, Clock, Filter, ChevronDown, ChevronUp, Brain, Copy, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

const SearchResults = ({ query, results, onSearch, isLoading }) => {
  const [searchQuery, setSearchQuery] = useState(query || '');
  const [selectedFilters, setSelectedFilters] = useState([]);
  const [sortBy, setSortBy] = useState('relevance');
  const [expandedSource, setExpandedSource] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  const filterOptions = [
    { value: 'facts', label: 'Facts', count: 0 },
    { value: 'grounds', label: 'Legal Grounds', count: 0 },
    { value: 'prayers', label: 'Prayers', count: 0 },
    { value: 'judgment', label: 'Judgment', count: 0 }
  ];

  // Update filter counts based on results
  if (results?.sources) {
    filterOptions.forEach(filter => {
      filter.count = results.sources.filter(source => 
        source.section === filter.value
      ).length;
    });
  }

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery, selectedFilters.length > 0 ? selectedFilters : null);
    }
  };

  const handleFilterToggle = (filter) => {
    setSelectedFilters(prev => 
      prev.includes(filter)
        ? prev.filter(f => f !== filter)
        : [...prev, filter]
    );
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getSortedSources = () => {
    if (!results?.sources) return [];
    
    let filtered = results.sources;
    
    // Apply filters
    if (selectedFilters.length > 0) {
      filtered = filtered.filter(source => 
        selectedFilters.includes(source.section)
      );
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'relevance':
          return b.similarity_score - a.similarity_score;
        case 'filename':
          return a.filename.localeCompare(b.filename);
        default:
          return 0;
      }
    });

    return sorted;
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getSectionColor = (section) => {
    const colors = {
      facts: 'bg-blue-100 text-blue-800',
      grounds: 'bg-green-100 text-green-800',
      prayers: 'bg-purple-100 text-purple-800',
      judgment: 'bg-orange-100 text-orange-800',
      general: 'bg-gray-100 text-gray-800'
    };
    return colors[section] || colors.general;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8">
          <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search legal judgments..."
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center space-x-2"
              >
                <Filter className="h-4 w-4" />
                <span>Filters</span>
                {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              
              <motion.button
                type="submit"
                disabled={isLoading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Searching...' : 'Search'}
              </motion.button>
            </div>
          </form>

          {/* Filters Panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 pt-4 border-t border-gray-200"
              >
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="text-sm font-medium text-gray-600 self-center mr-2">Section:</span>
                  {filterOptions.map((filter) => (
                    <button
                      key={filter.value}
                      onClick={() => handleFilterToggle(filter.value)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                        selectedFilters.includes(filter.value)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {filter.label} ({filter.count})
                    </button>
                  ))}
                </div>
                
                <div className="flex items-center space-x-4">
                  <label className="text-sm font-medium text-gray-600">Sort by:</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-1.5 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="relevance">Relevance</option>
                    <option value="filename">Filename</option>
                  </select>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Results */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <span className="ml-4 text-lg text-gray-600">Searching...</span>
          </div>
        ) : results ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* AI Analysis */}
            <div className="lg:col-span-2">
              {results.answer && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 mb-8 border border-blue-200"
                >
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                      <Brain className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">AI Analysis</h2>
                      <p className="text-sm text-gray-600">Generated insights from legal precedents</p>
                    </div>
                    <button
                      onClick={() => copyToClipboard(results.answer)}
                      className="ml-auto p-2 text-gray-500 hover:text-gray-700 hover:bg-white rounded-lg transition-colors"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  
                  <div className="prose prose-sm max-w-none text-gray-700">
                    <div className="whitespace-pre-wrap">{results.answer}</div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Sources Sidebar */}
            <div>
              <div className="sticky top-24">
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Sources</h3>
                    <span className="text-sm text-gray-500">
                      {getSortedSources().length} results
                    </span>
                  </div>
                  
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {getSortedSources().map((source, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                        onClick={() => setExpandedSource(expandedSource === index ? null : index)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <FileText className="h-4 w-4 text-gray-500 flex-shrink-0" />
                            <h4 className="font-medium text-sm text-gray-900 truncate">
                              {source.filename}
                            </h4>
                          </div>
                          
                          <div className={`px-2 py-1 rounded text-xs font-medium ${getScoreColor(source.similarity_score)}`}>
                            {(source.similarity_score * 100).toFixed(0)}%
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSectionColor(source.section)}`}>
                            {source.section?.charAt(0).toUpperCase() + source.section?.slice(1)}
                          </span>
                        </div>
                        
                        <p className="text-sm text-gray-600 line-clamp-2">
                          {source.preview}
                        </p>
                        
                        <AnimatePresence>
                          {expandedSource === index && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="mt-3 pt-3 border-t border-gray-200"
                            >
                              <div className="space-y-2 text-sm">
                                <div>
                                  <span className="font-medium text-gray-700">Full Content:</span>
                                  <p className="text-gray-600 mt-1 whitespace-pre-wrap">
                                    {source.metadata?.content || source.preview}
                                  </p>
                                </div>
                                
                                <div className="flex items-center justify-between pt-2">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      copyToClipboard(source.preview);
                                    }}
                                    className="flex items-center space-x-1 text-blue-600 hover:text-blue-700"
                                  >
                                    <Copy className="h-3 w-3" />
                                    <span className="text-xs">Copy</span>
                                  </button>
                                  
                                  <span className="text-xs text-gray-500">
                                    Score: {source.similarity_score.toFixed(3)}
                                  </span>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No search performed yet</h3>
            <p className="text-gray-600">Enter a query above to search through legal judgments</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchResults;