import React, { useState, useEffect } from 'react';
import { FiZap, FiSearch, FiDownload, FiRefreshCw, FiLoader, FiBriefcase, FiGlobe, FiMail, FiLinkedin, FiX, FiCpu, FiFile, FiBarChart2, FiCheck, FiEdit, FiSave, FiTrash2, FiMapPin, FiPhone, FiChevronDown } from 'react-icons/fi';
import './WebScrapingTab.css';

const WebScrapingTab = () => {
  const [formData, setFormData] = useState({
    jobTitle: '',
    location: '',
    industry: '',
    leadLimit: 5
  });
  
  const [suggestions, setSuggestions] = useState({
    jobTitle: [],
    location: [],
    industry: []
  });
  
  const [showSuggestions, setShowSuggestions] = useState({
    jobTitle: false,
    location: false,
    industry: false
  });
  
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [showError, setShowError] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [openDropdowns, setOpenDropdowns] = useState({});

  const suggestionLists = {
    jobTitle: ['CEO', 'CTO', 'CFO', 'CMO', 'Director', 'Manager', 'Founder', 'President', 'VP', 'Head of'],
    location: ['New York', 'San Francisco', 'London', 'Berlin', 'Tokyo', 'Singapore', 'Toronto', 'Sydney'],
    industry: ['Technology', 'Healthcare', 'Finance', 'Education', 'Manufacturing', 'Retail', 'Real Estate', 'Marketing']
  };

  useEffect(() => {
    loadSuggestions();
  }, []);

  const loadSuggestions = async () => {
    try {
      console.log('Suggestions loaded');
    } catch (error) {
      console.log('Could not load suggestions from API');
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    if (value.length > 0) {
      const filtered = suggestionLists[field].filter(item => 
        item.toLowerCase().includes(value.toLowerCase())
      );
      setSuggestions(prev => ({
        ...prev,
        [field]: filtered
      }));
      setShowSuggestions(prev => ({
        ...prev,
        [field]: filtered.length > 0
      }));
    } else {
      setShowSuggestions(prev => ({
        ...prev,
        [field]: false
      }));
    }
  };

  const selectSuggestion = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    setShowSuggestions(prev => ({
      ...prev,
      [field]: false
    }));
  };

  const hideSuggestions = (field) => {
    setTimeout(() => {
      setShowSuggestions(prev => ({
        ...prev,
        [field]: false
      }));
    }, 200);
  };

  const toggleDropdown = (leadId) => {
    setOpenDropdowns(prev => ({
      ...prev,
      [leadId]: !prev[leadId]
    }));
  };

  const generateLeads = async () => {
    const { jobTitle, location, industry, leadLimit } = formData;

    if (!jobTitle.trim()) {
        showErrorMsg('Please enter at least one job title');
        return;
    }

    setLoading(true);
    setProgress(0);
    setOpenDropdowns({});

    try {
        let query = `site:linkedin.com/in "${jobTitle}"`;
        
        if (location.trim()) {
            query += ` "${location}"`;
        }
        
        if (industry.trim()) {
            query += ` "${industry}"`;
        }
        
        query += ` "@gmail.com"`;

        const requestData = {
            query: query,
            max_leads: leadLimit
        };

        console.log("Sending query:", query);

        const progressInterval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 85) {
                    clearInterval(progressInterval);
                    return 85;
                }
                return prev + 2 + Math.random() * 3;
            });
        }, 600);

        const response = await fetch('/webscraping/generate-leads', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        clearInterval(progressInterval);
        setProgress(100);

        await new Promise(resolve => setTimeout(resolve, 800));

        const data = await response.json();
        console.log(data)
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate leads');
        }

        setResults(data);
        setLoading(false);

    } catch (error) {
        setLoading(false);
        showErrorMsg(error.message);
    }
};

  const showErrorMsg = (message) => {
    setError(message);
    setShowError(true);
  };

  const hideError = () => {
    setShowError(false);
    setError('');
  };

  const exportLeads = (format = 'csv') => {
  if (!results || !results.leads || results.leads.length === 0) {
    showErrorMsg('No results to export');
    return;
  }

  try {
    let content, mimeType, extension;

    switch (format) {
      case 'json':
        content = JSON.stringify({
          generated_at: results.generated_at,
          summary: results.summary,
          leads: results.leads
        }, null, 2);
        mimeType = 'application/json';
        extension = 'json';
        break;
        
      case 'csv':
      default:
        const headers = [
          'Name', 'Job Title', 'Company', 'Location', 'Industry', 
          'Domain', 'Lead Score', 'LinkedIn URL', 
          'Validated Emails', 'Phone Numbers', 
          'Search Emails', 'Search Phones'
        ];
        
        const csvContent = results.leads.map(lead => {
          const allEmails = lead.all_emails || [];
          const phoneNumbers = lead.phone_numbers || [];
          const searchEmails = lead.search_emails || [];
          const searchPhones = lead.search_phones || [];
          
          return [
            `"${lead.name || 'N/A'}"`,
            `"${lead.job_title || 'N/A'}"`,
            `"${lead.company || 'N/A'}"`,
            `"${lead.location || 'N/A'}"`,
            `"${lead.industry || 'N/A'}"`,
            `"${lead.domain || 'N/A'}"`,
            lead.lead_score || 0,
            `"${lead.url || 'N/A'}"`,
            `"${allEmails.map(e => e.email).join('; ')}"`,
            `"${phoneNumbers.map(p => p.phone).join('; ')}"`,
            `"${searchEmails.map(e => e.email).join('; ')}"`,
            `"${searchPhones.map(p => p.phone).join('; ')}"`
          ].join(',');
        });
        
        content = [headers.join(','), ...csvContent].join('\n');
        mimeType = 'text/csv;charset=utf-8;';
        extension = 'csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `enhanced-leads-${new Date().toISOString().split('T')[0]}.${extension}`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setError(`Leads exported as ${format.toUpperCase()} successfully!`);
    setShowError(true);
    
  } catch (error) {
    showErrorMsg('Failed to export leads: ' + error.message);
  }
};

  const newSearch = () => {
    setResults(null);
    setFormData({
      jobTitle: '',
      location: '',
      industry: '',
      leadLimit: 5
    });
    setOpenDropdowns({});
  };

  const clearForm = () => {
    if (window.confirm("Are you sure you want to clear all search criteria?")) {
      setFormData({
        jobTitle: '',
        location: '',
        industry: '',
        leadLimit: 5
      });
    }
  };

  const saveSearchCriteria = () => {
    localStorage.setItem('savedSearchCriteria', JSON.stringify(formData));
    showErrorMsg('Search criteria saved successfully!');
  };

  const loadSearchCriteria = () => {
    const saved = localStorage.getItem('savedSearchCriteria');
    if (saved) {
      setFormData(JSON.parse(saved));
      showErrorMsg('Search criteria loaded successfully!');
    } else {
      showErrorMsg('No saved search criteria found!');
    }
  };

  const generateLeadKey = (lead, index) => {
    if (lead.url) {
      return `${lead.url}-${index}`;
    }
    if (lead.name) {
      return `${lead.name}-${index}`;
    }
    return `lead-${index}`;
  };

  const createEnhancedLeadCard = (lead, index) => {
    const allEmails = lead.all_emails || [];
    const phoneNumbers = lead.phone_numbers || [];
    const searchEmails = lead.search_emails || [];
    const searchPhones = lead.search_phones || [];
    const employees = lead.employees || [];
    const companyInfo = lead.company_info || {};
    const leadId = generateLeadKey(lead, index);
    const isOpen = openDropdowns[leadId] || false;

    return (
      <div key={leadId} className="lead-card">
        {/* Header with Dropdown Toggle */}
        <div 
          className="lead-card-header"
          onClick={() => toggleDropdown(leadId)}
        >
          <div className="lead-name">{lead.name || 'Unknown'}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <div className="lead-score">Score: {lead.lead_score || 0}</div>
            <FiChevronDown 
              className={`dropdown-arrow ${isOpen ? 'open' : ''}`}
            />
          </div>
        </div>
        
        {/* Collapsible Content */}
        <div className={`lead-card-content ${isOpen ? 'open' : ''}`}>
          {/* Main Details */}
          <div className="lead-details">
            <div className="detail-item">
              <FiBriefcase />
              <span>{lead.job_title || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <FiBriefcase />
              <span>{lead.company || 'N/A'}</span>
            </div>
            {lead.location && (
              <div className="detail-item">
                <FiMapPin />
                <span>{lead.location}</span>
              </div>
            )}
            {lead.industry && (
              <div className="detail-item">
                <FiGlobe />
                <span>{lead.industry}</span>
              </div>
            )}
            <div className="detail-item">
              <FiMail />
              <span>{allEmails.length} validated emails</span>
            </div>
            <div className="detail-item">
              <FiPhone />
              <span>{phoneNumbers.length} phone numbers</span>
            </div>
            {lead.domain && (
              <div className="detail-item">
                <FiGlobe />
                <span>Domain: {lead.domain}</span>
              </div>
            )}
          </div>

          {/* Company Information */}
          {companyInfo.name && (
            <div className="company-section">
              <div className="section-title">Company Information</div>
              <div className="company-details">
                {companyInfo.name && <span className="company-name">{companyInfo.name}</span>}
                {companyInfo.description && (
                  <div className="company-description">{companyInfo.description}</div>
                )}
              </div>
            </div>
          )}

          {/* Search-found Contacts */}
          {(searchEmails.length > 0 || searchPhones.length > 0) && (
            <div className="contacts-section">
              <div className="section-title">Found in Search Results</div>
              <div className="contact-list">
                {searchEmails.map((email, emailIndex) => (
                  <span key={`search-email-${emailIndex}`} className="contact-badge email">
                    <FiMail />
                    {email.email} (Score: {email.score})
                  </span>
                ))}
                {searchPhones.map((phone, phoneIndex) => (
                  <span key={`search-phone-${phoneIndex}`} className="contact-badge phone">
                    <FiPhone />
                    {phone.phone} ({phone.type})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Validated Emails Section */}
          <div className="emails-section">
            <div className="section-title">Validated Emails</div>
            {allEmails.length > 0 ? (
              <div className="email-list">
                {allEmails.map((email, emailIndex) => (
                  <div key={`email-${emailIndex}`} className="email-item">
                    <span className={`email-address ${email.score > 80 ? 'high-score' : email.score > 60 ? 'medium-score' : 'low-score'}`}>
                      <FiMail />
                      {email.email}
                    </span>
                    <div className="email-details">
                      <span className="email-score">Score: {email.score}</span>
                      <span className="email-source">Source: {email.source}</span>
                      {email.smtp_valid && <span className="email-verified">✓ SMTP Verified</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-data">No validated emails found</div>
            )}
          </div>

          {/* Phone Numbers Section */}
          <div className="phones-section">
            <div className="section-title">Phone Numbers</div>
            {phoneNumbers.length > 0 ? (
              <div className="phone-list">
                {phoneNumbers.map((phone, phoneIndex) => (
                  <div key={`phone-${phoneIndex}`} className="phone-item">
                    <span className="phone-number">
                      <FiPhone />
                      {phone.phone}
                    </span>
                    <div className="phone-details">
                      <span className="phone-type">Type: {phone.type}</span>
                      <span className="phone-source">Source: {phone.source}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-data">No phone numbers found</div>
            )}
          </div>

          {/* Employees from Company Website */}
          {employees.length > 0 && (
            <div className="employees-section">
              <div className="section-title">Team Members Found</div>
              <div className="employees-list">
                {employees.slice(0, 5).map((employee, empIndex) => (
                  <div key={`employee-${empIndex}`} className="employee-item">
                    <span className="employee-name">{employee.name}</span>
                    {employee.role && <span className="employee-role">{employee.role}</span>}
                    {employee.email && <span className="employee-email">{employee.email}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LinkedIn Profile Link */}
          {lead.url && (
            <div className="lead-actions">
              <a href={lead.url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                <FiLinkedin /> View LinkedIn Profile
              </a>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Loading State with Enhanced Animation
  if (loading) {
    return (
      <div className="webscraping-container">
        <div className="loading-section">
          <div className="webscraping-card-header">
            <div className="webscraping-card-icon-wrapper">
              <FiCpu className="webscraping-card-main-icon spinning" />
            </div>
            <h3>Generating Leads...</h3>
          </div>
          
          <div className="progress-stats">
            <div className="progress-stat">
              <span className="progress-stat-value">{Math.round(progress)}%</span>
              <span className="progress-stat-label">Complete</span>
            </div>
          </div>
          
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
          
          <p>Searching LinkedIn profiles and scraping company data...</p>
          
          <div className="status-badge status-running">
            <FiLoader className="spinning" />
            Status: {progress < 100 ? 'Running' : 'Finalizing'}
          </div>

          {/* Progress Steps */}
          <div className="progress-steps">
            <div className={`progress-step ${progress >= 20 ? 'completed' : progress >= 10 ? 'active' : ''}`}>
              <div className="step-label">Searching</div>
            </div>
            <div className={`progress-step ${progress >= 50 ? 'completed' : progress >= 30 ? 'active' : ''}`}>
              <div className="step-label">Scraping</div>
            </div>
            <div className={`progress-step ${progress >= 80 ? 'completed' : progress >= 60 ? 'active' : ''}`}>
              <div className="step-label">Validating</div>
            </div>
            <div className={`progress-step ${progress >= 100 ? 'completed' : progress >= 90 ? 'active' : ''}`}>
              <div className="step-label">Finalizing</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Results State
  if (results) {
    return (
      <div className="webscraping-container">
        <div className="results-section">
          <div className="webscraping-card-header">
            <div className="webscraping-card-icon-wrapper">
              <FiFile className="webscraping-card-main-icon" />
            </div>
            <div>
              <h2>Lead Generation Results</h2>
              <p>{results.summary?.total_leads || 0} leads found</p>
            </div>
          </div>

          {/* ENHANCED Summary Section */}
          <div className="summary">
            <div className="summary-item">
              <div className="summary-value">{results.summary?.total_leads || 0}</div>
              <div className="summary-label">Total Leads</div>
            </div>
            <div className="summary-item">
              <div className="summary-value">{results.summary?.leads_with_emails || 0}</div>
              <div className="summary-label">With Emails</div>
            </div>
            <div className="summary-item">
              <div className="summary-value">{results.summary?.leads_with_phones || 0}</div>
              <div className="summary-label">With Phones</div>
            </div>
            <div className="summary-item">
              <div className="summary-value">{results.summary?.leads_with_location || 0}</div>
              <div className="summary-label">With Location</div>
            </div>
            <div className="summary-item">
              <div className="summary-value">{results.summary?.leads_with_industry || 0}</div>
              <div className="summary-label">With Industry</div>
            </div>
          </div>

          {/* Data Breakdown */}
          {results.data_breakdown && (
            <div className="data-breakdown">
              <h4>Data Breakdown:</h4>
              <div className="breakdown-stats">
                <span>📧 {results.data_breakdown.emails_found} emails</span>
                <span>📞 {results.data_breakdown.phones_found} phones</span>
                <span>🔍 {results.data_breakdown.search_emails_found} search emails</span>
                <span>📱 {results.data_breakdown.search_phones_found} search phones</span>
              </div>
            </div>
          )}

          <div id="leadsContainer">
            {results.leads && results.leads.length > 0 ? (
              results.leads.map((lead, index) => createEnhancedLeadCard(lead, index))
            ) : (
              <div className="no-leads">No leads found. Try different search terms.</div>
            )}
          </div>

          <div className="actions">
            <div className="export-options">
              <button className="btn btn-primary" onClick={() => exportLeads('csv')}>
                <FiDownload /> Export as CSV
              </button>
              <button className="btn btn-primary" onClick={() => exportLeads('json')}>
                <FiDownload /> Export as JSON
              </button>
            </div>
            <div className="action-buttons">
              <button className="btn btn-secondary" onClick={newSearch}>
                <FiRefreshCw /> New Search
              </button>
              <button className="btn btn-secondary" onClick={saveSearchCriteria}>
                <FiSave /> Save Criteria
              </button>
            </div>
          </div>
        </div>

        {showError && (
          <div className="modal">
            <div className="modal-content">
              <span className="close" onClick={hideError}><FiX /></span>
              <h3>{error.includes('successfully') ? 'Success' : 'Error'}</h3>
              <p>{error}</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Main Form State
  return (
    <div className="webscraping-container">
      <div className="webscraping-card-header">
        <div className="webscraping-card-icon-wrapper">
          <FiZap className="webscraping-card-main-icon" />
        </div>
        <div>
          <h1>LinkedIn Lead Generator</h1>
          <p>Find professional contacts with email addresses using AI-powered web scraping</p>
        </div>
      </div>

      <div className="webscraping-content">
        <div className="input-section">
          <div className="form-group">
            <label htmlFor="jobTitle">Job Title/Keywords *</label>
            <input
              type="text"
              id="jobTitle"
              value={formData.jobTitle}
              onChange={(e) => handleInputChange('jobTitle', e.target.value)}
              onFocus={() => setShowSuggestions(prev => ({ ...prev, jobTitle: true }))}
              onBlur={() => hideSuggestions('jobTitle')}
              placeholder="e.g., CEO, CTO, Marketing Manager"
            />
            <div className={`suggestions ${showSuggestions.jobTitle ? 'show' : ''}`}>
              {suggestions.jobTitle.map((item, index) => (
                <div key={`jobTitle-${index}`} className="suggestion-item" onClick={() => selectSuggestion('jobTitle', item)}>
                  {item}
                </div>
              ))}
            </div>
            <div className="help-text">Separate multiple titles with commas</div>
          </div>

          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input
              type="text"
              id="location"
              value={formData.location}
              onChange={(e) => handleInputChange('location', e.target.value)}
              onFocus={() => setShowSuggestions(prev => ({ ...prev, location: true }))}
              onBlur={() => hideSuggestions('location')}
              placeholder="e.g., New York, London"
            />
            <div className={`suggestions ${showSuggestions.location ? 'show' : ''}`}>
              {suggestions.location.map((item, index) => (
                <div key={`location-${index}`} className="suggestion-item" onClick={() => selectSuggestion('location', item)}>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="industry">Industry</label>
            <input
              type="text"
              id="industry"
              value={formData.industry}
              onChange={(e) => handleInputChange('industry', e.target.value)}
              onFocus={() => setShowSuggestions(prev => ({ ...prev, industry: true }))}
              onBlur={() => hideSuggestions('industry')}
              placeholder="e.g., Technology, Healthcare"
            />
            <div className={`suggestions ${showSuggestions.industry ? 'show' : ''}`}>
              {suggestions.industry.map((item, index) => (
                <div key={`industry-${index}`} className="suggestion-item" onClick={() => selectSuggestion('industry', item)}>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="leadLimit">Lead Limit</label>
            <input
              type="number"
              id="leadLimit"
              value={formData.leadLimit}
              onChange={(e) => handleInputChange('leadLimit', parseInt(e.target.value) || 5)}
              min="1"
              max="20"
            />
            <div className="help-text">Number of leads to generate (1-20)</div>
          </div>

          <div className="form-controls">
            <button className="btn btn-primary generate-btn" onClick={generateLeads}>
              <FiZap /> Generate Leads
            </button>
            
            <div className="secondary-controls">
              <button className="btn btn-secondary" onClick={loadSearchCriteria}>
                <FiFile /> Load Criteria
              </button>
              <button className="btn btn-clear" onClick={clearForm}>
                <FiTrash2 /> Clear All
              </button>
            </div>
          </div>
        </div>
      </div>

      {showError && (
        <div className="modal">
          <div className="modal-content">
            <span className="close" onClick={hideError}><FiX /></span>
            <h3>Error</h3>
            <p>{error}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default WebScrapingTab;
