import React, { useState, useRef } from 'react';
import axios from 'axios';
import { saveAs } from 'file-saver';
import * as XLSX from 'xlsx';
import './EmailValidator.css';

// React Icons
import { 
  FiUploadCloud, 
  FiDownload, 
  FiMail, 
  FiRefreshCw,
  FiCheck,
  FiFile,
  FiUsers,
  FiBarChart2,
  FiTrash2,
  FiX
} from 'react-icons/fi';

const EmailValidator = () => {
    const [file, setFile] = useState(null);
    const [processedData, setProcessedData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef(null);

    // THIS WAS THE PROBLEM — NOW FIXED!
    const API_BASE_URL = 'https://65.1.129.37/api';

    // Drag and drop handlers
    const handleDragOver = (e) => {
        e.preventDefault();
        setDragOver(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setDragOver(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    };

    const handleFileSelect = (selectedFile) => {
        setFile(selectedFile);
        setError('');
        setSuccess('');
        setProcessedData(null);
    };

    const handleFileInputChange = (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    };

    // Delete file function
    const handleDeleteFile = () => {
        setFile(null);
        setError('');
        setSuccess('');
        setProcessedData(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    // Clear results function
    const handleClearResults = () => {
        setProcessedData(null);
        setSuccess('');
    };

    const processFile = async () => {
        if (!file) {
            setError('Please select a file first');
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            // NOW CALLING THE CORRECT ENDPOINT → /api/upload-file
            const response = await axios.post(`${API_BASE_URL}/upload-file`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                timeout: 300000, // 5 minutes timeout for large files
            });

            if (response.data.status === 'success') {
                setProcessedData(response.data);
                setSuccess(`Successfully processed ${response.data.total_records_processed} records`);
            } else {
                throw new Error(response.data.error || 'Unknown error occurred');
            }
        } catch (error) {
            console.error('Upload error:', error);
            if (error.code === 'ECONNABORTED') {
                setError('Request timeout - file may be too large or server is busy');
            } else {
                setError(`Error: ${error.response?.data?.error || error.message}`);
            }
        } finally {
            setLoading(false);
        }
    };

    const getScoreClass = (score) => {
        if (score >= 80) return 'score-high';
        if (score >= 60) return 'score-medium';
        return 'score-low';
    };

    const escapeCsvValue = (value) => {
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        return stringValue.replace(/"/g, '""').replace(/\n/g, ' ');
    };

    const downloadCSV = () => {
        if (!processedData?.results?.length) return;

        const firstResult = processedData.results[0];
        const originalColumns = firstResult?.original_data ? Object.keys(firstResult.original_data) : [];
        const emailColumns = ['Domain', 'Best Email', 'Score', 'All Valid Emails'];
        const allHeaders = [...originalColumns, ...emailColumns];

        const csvContent = [
            allHeaders.join(','),
            ...processedData.results.map(result => {
                const originalValues = originalColumns.map(col => {
                    const value = result.original_data?.[col] || '';
                    return `"${escapeCsvValue(value)}"`;
                });
                
                const emailValues = [
                    `"${result.domain || ''}"`,
                    `"${result.best_email?.email || ''}"`,
                    result.best_email?.score || '',
                    `"${result.valid_emails_with_scores?.map(e => e.email).join('; ') || ''}"`
                ];
                
                return [...originalValues, ...emailValues].join(',');
            })
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
        saveAs(blob, 'enhanced_leads_with_emails.csv');
    };

    const downloadJSON = () => {
        if (!processedData) return;
        
        const enhancedData = processedData.results.map(result => ({
            ...result.original_data,
            domain: result.domain,
            best_email: result.best_email?.email || null,
            email_score: result.best_email?.score || null,
            all_valid_emails: result.valid_emails_with_scores?.map(e => e.email) || [],
            generated_emails: result.generated_emails || []
        }));
        
        const jsonContent = JSON.stringify(enhancedData, null, 2);
        const blob = new Blob([jsonContent], { type: 'application/json' });
        saveAs(blob, 'enhanced_leads_with_emails.json');
    };

    const downloadExcel = () => {
        if (!processedData?.results?.length) return;

        const firstResult = processedData.results[0];
        const originalColumns = firstResult?.original_data ? Object.keys(firstResult.original_data) : [];
        const emailColumns = ['Domain', 'Best Email', 'Score', 'All Valid Emails'];
        const allHeaders = [...originalColumns, ...emailColumns];

        const worksheetData = [
            allHeaders,
            ...processedData.results.map(result => {
                const originalValues = originalColumns.map(col => result.original_data?.[col] || '');
                const emailValues = [
                    result.domain || '',
                    result.best_email?.email || '',
                    result.best_email?.score || '',
                    result.valid_emails_with_scores?.map(e => e.email).join('; ') || ''
                ];
                return [...originalValues, ...emailValues];
            })
        ];

        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Email Results');
        XLSX.writeFile(workbook, 'enhanced_leads_with_emails.xlsx');
    };

    return (
        <div className="email-validator-container">
            <div className="email-validator-wrapper">
                {/* Upload Card */}
                <div className="card">
                    <div className="card-header">
                        <div className="card-icon-wrapper">
                            <FiUploadCloud className="card-main-icon" />
                        </div>
                        <h3>Email Validator & Finder</h3>
                    </div>
                    
                    <div className="card-section">
                        <h4 className="section-title">
                            <FiFile className="section-icon" />
                            Upload Your File
                        </h4>
                        
                        <div 
                            className={`upload-section ${dragOver ? 'dragover' : ''}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="upload-icon">
                                <FiUploadCloud />
                            </div>
                            <p>Supported: CSV, Excel (.xlsx, .xls), Text (.txt)</p>
                            <p>Should contain names + company info</p>
                            <button 
                                className="btn btn-primary" 
                                onClick={() => fileInputRef.current?.click()}
                                style={{ marginTop: '15px' }}
                            >
                                <FiUploadCloud /> Choose File
                            </button>
                            <input 
                                type="file" 
                                ref={fileInputRef}
                                className="file-input" 
                                accept=".csv,.xlsx,.xls,.txt"
                                onChange={handleFileInputChange}
                            />
                        </div>
                        
                        {file && (
                            <div className="file-info">
                                <div className="file-info-header">
                                    <strong>Selected:</strong> {file.name}
                                    <button 
                                        className="btn-delete-file"
                                        onClick={handleDeleteFile}
                                        title="Remove file"
                                    >
                                        <FiTrash2 />
                                    </button>
                                </div>
                                <strong>Size:</strong> {(file.size / 1024).toFixed(2)} KB
                            </div>
                        )}
                        
                        {error && <div className="error">{error}</div>}
                        {success && <div className="success">{success}</div>}

                        <div className="controls" style={{ marginTop: '20px', gap: '10px', display: 'flex', flexWrap: 'wrap' }}>
                            <button 
                                className="btn btn-primary" 
                                onClick={processFile} 
                                disabled={!file || loading}
                            >
                                {loading ? (
                                    <>Processing...</>
                                ) : (
                                    <>Process File</>
                                )}
                            </button>
                            
                            {file && (
                                <button className="btn btn-secondary" onClick={handleDeleteFile} disabled={loading}>
                                    Delete File
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {loading && (
                    <div className="card">
                        <div className="loading">
                            <div className="spinner"></div>
                            <h3>Processing your file...</h3>
                            <p>Finding company domains and validating emails...</p>
                        </div>
                    </div>
                )}

                {processedData && (
                    <>
                        <div className="card">
                            <div className="card-header">
                                <div className="card-icon-wrapper">
                                    <FiBarChart2 className="card-main-icon" />
                                </div>
                                <div className="card-header-content">
                                    <h3>Results</h3>
                                    <button className="btn-clear-results" onClick={handleClearResults}>
                                        Clear
                                    </button>
                                </div>
                            </div>
                            
                            <div className="card-section">
                                <h4 className="section-title">Summary</h4>
                                <div className="summary-cards">
                                    <div className="summary-card">
                                        <h3>Total Records</h3>
                                        <div className="number">{processedData.total_records_processed}</div>
                                    </div>
                                    <div className="summary-card">
                                        <h3>Valid Emails</h3>
                                        <div className="number">{processedData.summary.valid_emails_found}</div>
                                    </div>
                                    <div className="summary-card">
                                        <h3>Domains Found</h3>
                                        <div className="number">{processedData.summary.domains_found}</div>
                                    </div>
                                    <div className="summary-card">
                                        <h3>Success Rate</h3>
                                        <div className="number">
                                            {processedData.summary.success_rate}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="card">
                            <div className="card-section">
                                <h4 className="section-title">Email Results</h4>
                                <ResultsTable data={processedData} getScoreClass={getScoreClass} />
                            </div>
                        </div>

                        <div className="card">
                            <div className="card-section">
                                <h4 className="section-title">Download Results</h4>
                                <div className="download-section">
                                    <button className="btn btn-primary download-btn" onClick={downloadCSV}>
                                        Download CSV
                                    </button>
                                    <button className="btn btn-primary download-btn" onClick={downloadJSON}>
                                        Download JSON
                                    </button>
                                    <button className="btn btn-primary download-btn" onClick={downloadExcel}>
                                        Download Excel
                                    </button>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

const ResultsTable = ({ data, getScoreClass }) => {
    const [expandedRows, setExpandedRows] = useState(new Set());

    const toggleDetails = (index) => {
        const newSet = new Set(expandedRows);
        newSet.has(index) ? newSet.delete(index) : newSet.add(index);
        setExpandedRows(newSet);
    };

    if (!data?.results?.length) return null;

    const firstResult = data.results[0];
    const originalColumns = firstResult?.original_data ? Object.keys(firstResult.original_data) : [];
    const emailColumns = ['Domain', 'Best Email', 'Score', 'All Valid Emails', 'Details'];
    const allHeaders = [...originalColumns, ...emailColumns];

    return (
        <div className="table-container">
            <table className="results-table">
                <thead>
                    <tr>
                        {allHeaders.map(header => <th key={header}>{header}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {data.results.map((result, index) => (
                        <React.Fragment key={index}>
                            <tr>
                                {originalColumns.map(col => (
                                    <td key={col}>{result.original_data?.[col] || 'N/A'}</td>
                                ))}
                                <td>{result.domain || 'N/A'}</td>
                                <td><strong>{result.best_email?.email || 'None'}</strong></td>
                                <td>
                                    {result.best_email && (
                                        <span className={`email-score ${getScoreClass(result.best_email.score)}`}>
                                            {result.best_email.score}
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {result.valid_emails_with_scores?.map(e => e.email).join(', ') || 'None'}
                                </td>
                                <td>
                                    <button className="toggle-details" onClick={() => toggleDetails(index)}>
                                        {expandedRows.has(index) ? 'Hide' : 'Details'}
                                    </button>
                                </td>
                            </tr>
                            {expandedRows.has(index) && (
                                <tr>
                                    <td colSpan={allHeaders.length} className="details-cell">
                                        <div className="email-details expanded">
                                            <strong>Generated Patterns:</strong> {result.generated_emails?.join(', ') || 'None'}<br/><br/>
                                            {result.valid_emails_with_scores && (
                                                <>
                                                    <strong>Valid Emails:</strong><br/>
                                                    <ul>
                                                        {result.valid_emails_with_scores.map((e, i) => (
                                                            <li key={i}>
                                                                {e.email} → Score: <strong>{e.score}</strong>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </React.Fragment>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default EmailValidator;
