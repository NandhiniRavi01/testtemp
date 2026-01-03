import React, { useState, useEffect } from "react";
import { 
  FiFile, FiMail, FiSettings, FiEye, FiBarChart2, 
  FiCheck, FiPaperclip, FiRefreshCw,
  FiX, FiPlus, FiSend, FiEdit, FiSave,
  FiMessageSquare, FiChevronDown, FiChevronUp,
  FiTrash2, FiCpu, FiLayers, FiUsers,
  FiUploadCloud, FiMessageCircle, FiAward
} from "react-icons/fi";
import "./AutoEmailTab.css";

function AutoEmailTab() {
  const [file, setFile] = useState(null);
  const [batchSize, setBatchSize] = useState(250);
  const [preview, setPreview] = useState({ columns: [], data: [] });
  const [showPreview, setShowPreview] = useState(false);
  const [progress, setProgress] = useState({ sent: 0, total: 0, status: "idle" });
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState({ preview: false, upload: false, generating: false });
  const [senderAccounts, setSenderAccounts] = useState([{ 
    email: "", 
    password: "", 
    sender_name: "" 
  }]);
  
  // Email content state
  const [emailContent, setEmailContent] = useState({
    subject: "",
    body: "",
    sender_name: ""
  });
  
  const [prompt, setPrompt] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  // Template state
  const [templateFile, setTemplateFile] = useState(null);
  const [useTemplates, setUseTemplates] = useState(false);
  const [positionColumn, setPositionColumn] = useState("position");
  const [loadedTemplates, setLoadedTemplates] = useState([]);
  const [templateDetails, setTemplateDetails] = useState([]);

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setPreview({ columns: [], data: [] });
    setShowPreview(false);
  };

  // Handle template file selection
  const handleTemplateFileChange = async (selectedFile) => {
    setTemplateFile(selectedFile);
    
    if (!selectedFile) {
      setLoadedTemplates([]);
      setTemplateDetails([]);
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://65.1.129.37:5000/upload-templates", {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setLoadedTemplates(data.positions || []);
        setTemplateDetails(data.templates || []);
        alert(`Successfully loaded ${data.positions.length} templates`);
      } else {
        alert("Error loading templates: " + data.error);
        setTemplateFile(null);
        setLoadedTemplates([]);
        setTemplateDetails([]);
      }
    } catch (err) {
      alert("Error loading templates: " + err.message);
      setTemplateFile(null);
      setLoadedTemplates([]);
      setTemplateDetails([]);
    }
  };

  // Delete uploaded file
  const handleDeleteFile = () => {
    if (window.confirm("Are you sure you want to remove the uploaded file?")) {
      setFile(null);
      setPreview({ columns: [], data: [] });
      setShowPreview(false);
      // Reset file input
      const fileInput = document.getElementById('fileInput');
      if (fileInput) fileInput.value = '';
    }
  };

  // Delete template file
  const handleDeleteTemplateFile = () => {
    if (window.confirm("Are you sure you want to remove the template file?")) {
      setTemplateFile(null);
      setLoadedTemplates([]);
      setTemplateDetails([]);
      // Reset template file input
      const templateFileInput = document.getElementById('templateFileInput');
      if (templateFileInput) templateFileInput.value = '';
    }
  };

  // Toggle preview dropdown
  const togglePreview = () => {
    if (!file) {
      alert("Please upload a file first!");
      return;
    }
    
    if (!showPreview && preview.data.length === 0) {
      handlePreview();
    } else {
      setShowPreview(!showPreview);
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Add sender account field
  const addSenderAccount = () => {
    setSenderAccounts([...senderAccounts, { email: "", password: "", sender_name: "" }]);
  };

  // Remove sender account field
  const removeSenderAccount = (index) => {
    if (senderAccounts.length <= 1) return;
    const updatedAccounts = [...senderAccounts];
    updatedAccounts.splice(index, 1);
    setSenderAccounts(updatedAccounts);
  };

  // Update sender account field
  const updateSenderAccount = (index, field, value) => {
    const updatedAccounts = [...senderAccounts];
    updatedAccounts[index][field] = value;
    setSenderAccounts(updatedAccounts);
  };

  // Generate email content using Gemini API
  const generateEmailContent = async () => {
    if (!prompt.trim()) {
      alert("Please enter a prompt to generate email content!");
      return;
    }

    setLoading({ ...loading, generating: true });
    try {
      const res = await fetch("http://65.1.129.37:5000/generate-content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setEmailContent(data);
        setIsEditing(false);
        localStorage.setItem('emailContent', JSON.stringify(data));
      } else {
        alert("Error generating content: " + data.error);
      }
    } catch (err) {
      alert("Error generating content: " + err.message);
    } finally {
      setLoading({ ...loading, generating: false });
    }
  };

  // Clear email content
  const clearEmailContent = async () => {
    if (window.confirm("Are you sure you want to clear all email content?")) {
      const clearedContent = {
        subject: "",
        body: "",
        sender_name: ""
      };
      
      setEmailContent(clearedContent);
      setIsEditing(false);
      localStorage.removeItem('emailContent');
      
      // Also clear on the backend
      try {
        await fetch("http://65.1.129.37:5000/update-content", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(clearedContent),
        });
      } catch (err) {
        console.error("Error clearing content on backend:", err);
      }
    }
  };

  // Update email content on the backend
  const updateEmailContent = async () => {
    try {
      const res = await fetch("http://65.1.129.37:5000/update-content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(emailContent),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setIsEditing(false);
        localStorage.setItem('emailContent', JSON.stringify(emailContent));
      } else {
        alert("Error updating content: " + data.error);
      }
    } catch (err) {
      alert("Error updating content: " + err.message);
    }
  };

  // Get stored email content
  const getEmailContent = async () => {
    try {
      const savedContent = localStorage.getItem('emailContent');
      if (savedContent) {
        setEmailContent(JSON.parse(savedContent));
      }

      const res = await fetch("http://65.1.129.37:5000/get-content");
      const data = await res.json();

      if (res.ok && data.subject) {
        setEmailContent(data);
        localStorage.setItem('emailContent', JSON.stringify(data));
      }
    } catch (err) {
      console.error("Error fetching email content:", err);
    }
  };

  // Preview uploaded file
  const handlePreview = async () => {
    if (!file) {
      alert("Please upload a file first!");
      return;
    }

    setLoading({ ...loading, preview: true });
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://65.1.129.37:5000/preview", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      
      if (res.ok) {
        setPreview(data);
        setShowPreview(true);
      } else {
        alert("Error fetching preview: " + data.error);
      }
    } catch (err) {
      alert("Error fetching preview: " + err.message);
    } finally {
      setLoading({ ...loading, preview: false });
    }
  };

  // Upload file and start sending emails
  const handleUpload = async () => {
    if (!file) {
      alert("Please upload a file first!");
      return;
    }

    if (useTemplates && (!templateFile || loadedTemplates.length === 0)) {
      alert("Please upload a valid template file first!");
      return;
    }

    if (!useTemplates && (!emailContent.subject || !emailContent.body || !emailContent.sender_name)) {
      alert("Please generate or enter email content first!");
      return;
    }

    const validAccounts = senderAccounts.filter(acc => acc.email && acc.password);
    if (validAccounts.length === 0) {
      alert("Please add at least one valid sender email and password!");
      return;
    }

    setLoading({ ...loading, upload: true });
    const formData = new FormData();
    formData.append("file", file);
    formData.append("batch_size", batchSize);
    formData.append("use_templates", useTemplates.toString());
    formData.append("position_column", positionColumn);
    
    // Only include email content if not using templates
    if (!useTemplates) {
      formData.append("subject", emailContent.subject);
      formData.append("body", emailContent.body);
      formData.append("sender_name", emailContent.sender_name);
    }
    
    // Include sender names with accounts
    senderAccounts.forEach(account => {
      if (account.email && account.password) {
        formData.append("sender_emails[]", account.email);
        formData.append("sender_passwords[]", account.password);
        formData.append("sender_names[]", account.sender_name || "");
      }
    });

    try {
      const res = await fetch("http://65.1.129.37:5000/upload", {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setSending(true);
        setProgress({ sent: 0, total: 0, status: "running" });
      } else {
        alert("Error uploading file: " + data.error);
      }
    } catch (err) {
      alert("Error uploading file: " + err.message);
    } finally {
      setLoading({ ...loading, upload: false });
    }
  };

  // Poll backend for progress
  useEffect(() => {
    let interval;
    if (sending) {
      interval = setInterval(async () => {
        try {
          const res = await fetch("http://65.1.129.37:5000/progress");
          const data = await res.json();
          setProgress(data);

          if (data.status === "completed" || data.status.startsWith("error")) {
            clearInterval(interval);
            setSending(false);
          }
        } catch (err) {
          console.error("Error fetching progress:", err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [sending]);

  // Get email content on component mount
  useEffect(() => {
    getEmailContent();
  }, []);

  // Calculate progress percentage
  const progressPercentage = progress.total > 0 ? (progress.sent / progress.total) * 100 : 0;

  return (
    <>
      {/* Content Generation Card */}
      <div className="card content-generation-card">
        <div className="card-header">
          <div className="card-icon-wrapper">
            <FiAward className="card-main-icon" />
          </div>
          <h3>AI Content Generation</h3>
        </div>
        
        <div className="card-section">
          <h4 className="section-title">
            <FiMessageCircle className="section-icon" />
            Generate Content with AI
          </h4>
          <div className="prompt-container">
            <textarea
              placeholder="Describe your business, target audience, or enter a prompt for the AI to generate email content..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="prompt-input"
            />
            <button 
              className="btn btn-generate" 
              onClick={generateEmailContent}
              disabled={loading.generating}
            >
              {loading.generating ? (
                <>
                  <div className="loading-spinner"></div>
                  Generating...
                </>
              ) : (
                <>
                  <FiCpu /> Generate Content
                </>
              )}
            </button>
          </div>
        </div>

        <div className="card-section">
          <h4 className="section-title">
            <FiEdit className="section-icon" />
            Email Content
          </h4>
          
          <div className="content-field">
            <label>Sender Name:</label>
            {isEditing ? (
              <input
                type="text"
                value={emailContent.sender_name}
                onChange={(e) => setEmailContent({...emailContent, sender_name: e.target.value})}
                className="content-input"
                placeholder="Not set"
              />
            ) : (
              <div className="content-display">
                {emailContent.sender_name || "Not set"}
              </div>
            )}
          </div>

          <div className="content-field">
            <label>Subject:</label>
            {isEditing ? (
              <input
                type="text"
                value={emailContent.subject}
                onChange={(e) => setEmailContent({...emailContent, subject: e.target.value})}
                className="content-input"
                placeholder="Not set"
              />
            ) : (
              <div className="content-display">
                {emailContent.subject || "Not set"}
              </div>
            )}
          </div>

          <div className="content-field">
            <label>Body:</label>
            {isEditing ? (
              <textarea
                value={emailContent.body}
                onChange={(e) => setEmailContent({...emailContent, body: e.target.value})}
                rows={6}
                className="content-textarea"
                placeholder="Not set"
              />
            ) : (
              <div className="content-display body-display">
                {emailContent.body || "Not set"}
              </div>
            )}
          </div>

          <div className="content-controls">
            {isEditing ? (
              <div className="button-group">
                <button className="btn btn-primary" onClick={updateEmailContent}>
                  <FiSave /> Save Changes
                </button>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setIsEditing(false)}
                >
                  <FiX /> Cancel
                </button>
              </div>
            ) : (
              <div className="button-group">
                <button className="btn btn-secondary" onClick={() => setIsEditing(true)}>
                  <FiEdit /> Edit Content
                </button>
                <button 
                  className="btn btn-clear" 
                  onClick={clearEmailContent}
                >
                  <FiTrash2 /> Clear All
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Template Upload Card */}
      <div className="card template-upload-card">
        <div className="card-header">
          <div className="card-icon-wrapper">
            <FiLayers className="card-main-icon" />
          </div>
          <h3>Email Templates</h3>
        </div>
        
        <div className="card-section">
          <div className="content-field">
            <label style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
              <input
                type="checkbox"
                checked={useTemplates}
                onChange={(e) => setUseTemplates(e.target.checked)}
              />
              Use Position-Based Templates
            </label>
            <small style={{color: '#64748b', marginTop: '5px'}}>
              Upload an Excel file with templates for different positions
            </small>
          </div>

          {useTemplates && (
            <>
              <div className="file-upload-container">
                <div className="file-input-wrapper">
                  <input 
                    type="file" 
                    accept=".csv,.xlsx" 
                    onChange={(e) => handleTemplateFileChange(e.target.files[0])}
                    id="templateFileInput"
                  />
                  <div className={`file-input-display ${templateFile ? 'has-file' : ''}`}>
                    <div className="upload-icon">
                      {templateFile ? <FiCheck /> : <FiLayers />}
                    </div>
                    <div className="file-info">
                      {templateFile ? (
                        <>
                          <div className="file-name">{templateFile.name}</div>
                          <div className="file-size">{formatFileSize(templateFile.size)}</div>
                        </>
                      ) : (
                        <>
                          <div className="file-name">Upload Template File</div>
                          <div className="file-size">CSV/Excel with position, subject, body, sender_name columns</div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                {templateFile && (
                  <div className="controls" style={{marginTop: '10px'}}>
                    <button 
                      className="btn btn-clear" 
                      onClick={handleDeleteTemplateFile}
                      style={{padding: '8px 12px', fontSize: '0.85rem'}}
                    >
                      <FiTrash2 /> Remove Template
                    </button>
                  </div>
                )}
              </div>

              {loadedTemplates.length > 0 && (
                <div className="content-field">
                  <label>Loaded Templates:</label>
                  <div className="template-display-container">
                    {templateDetails.map((template, index) => (
                      <div key={index} className="template-item">
                        <div className="template-header">
                          <span className="template-position">{template.position}</span>
                          {template.sender_name && (
                            <span className="template-sender-badge">
                              Sender: {template.sender_name}
                            </span>
                          )}
                        </div>
                        <div className="template-subject">
                          <strong>Subject:</strong> {template.subject || 'No subject'}
                        </div>
                        <div className="template-body-preview">
                          <strong>Body Preview:</strong> {template.body ? `${template.body.substring(0, 50)}...` : 'No body'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="content-field">
                <label>Position Column Name:</label>
                <input
                  type="text"
                  value={positionColumn}
                  onChange={(e) => setPositionColumn(e.target.value)}
                  className="content-input"
                  placeholder="position"
                />
                <small style={{color: '#64748b'}}>
                  Name of the column in your data file that contains job positions
                </small>
              </div>

              {/* Template Sender Name Configuration */}
              <div className="content-field">
                <h4 className="section-title" style={{marginBottom: '15px'}}>
                  <FiUsers className="section-icon" />
                  Template Sender Names
                </h4>
                <div className="template-info-box">
                  <p style={{margin: '0 0 10px 0', color: '#64748b', fontSize: '0.9rem'}}>
                    <strong>Priority Order for Sender Names:</strong>
                  </p>
                  <ol className="template-priority-list">
                    <li>Account Sender Name (from Settings)</li>
                    <li>Template Sender Name (from uploaded file)</li>
                    <li>Extracted from Email Address (fallback)</li>
                  </ol>
                  <div className="template-format-info">
                    <strong>Template File Format:</strong>
                    <div style={{color: '#64748b', fontSize: '0.8rem', marginTop: '5px'}}>
                      Your Excel/CSV should include: <code>position</code>, <code>subject</code>, <code>body</code>, and optionally <code>sender_name</code> columns
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* File Upload Card */}
      <div className="card file-upload-card">
        <div className="card-header">
          <div className="card-icon-wrapper">
            <FiUploadCloud className="card-main-icon" />
          </div>
          <h3>File Upload</h3>
        </div>
        
        <div className="file-upload-container">
          <div className="file-input-wrapper">
            <input 
              type="file" 
              accept=".csv,.xlsx" 
              onChange={handleFileChange}
              id="fileInput"
            />
            <div className={`file-input-display ${file ? 'has-file' : ''}`}>
              <div className="upload-icon">
                {file ? <FiCheck /> : <FiPaperclip />}
              </div>
              <div className="file-info">
                {file ? (
                  <>
                    <div className="file-name">{file.name}</div>
                    <div className="file-size">{formatFileSize(file.size)}</div>
                  </>
                ) : (
                  <>
                    <div className="file-name">Click to upload file</div>
                    <div className="file-size">Supports CSV and Excel files</div>
                  </>
                )}
              </div>
            </div>
          </div>
          {file && (
            <div className="controls" style={{marginTop: '10px'}}>
              <button 
                className="btn btn-clear" 
                onClick={handleDeleteFile}
                style={{padding: '8px 12px', fontSize: '0.85rem'}}
              >
                <FiTrash2 /> Remove File
              </button>
            </div>
          )}
        </div>

        <div className="controls">
          <button 
            className="btn btn-preview" 
            onClick={togglePreview}
            disabled={!file || loading.preview}
          >
            {loading.preview ? (
              <>
                <div className="loading-spinner"></div>
                Loading...
              </>
            ) : (
              <>
                {showPreview ? <FiChevronUp /> : <FiChevronDown />}
                {showPreview ? "Hide Preview" : "Preview File"}
              </>
            )}
          </button>
        </div>

        {/* File Preview Section */}
        {showPreview && preview.data.length > 0 && (
          <div className="file-preview-section">
            <div className="preview-header">
              <h4>
                <FiEye className="section-icon" /> File Preview ({preview.data.length} rows shown)
              </h4>
            </div>
            <div className="table-container">
              <table className="preview-table">
                <thead>
                  <tr>
                    {preview.columns.map((col, index) => (
                      <th key={index}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.data.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {preview.columns.map((col, colIndex) => (
                        <td key={colIndex}>{row[col] || '-'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Settings Card */}
      <div className="card settings-card">
        <div className="card-header">
          <div className="card-icon-wrapper">
            <FiSettings className="card-main-icon" />
          </div>
          <h3>Email Settings</h3>
        </div>
        
        <div className="card-section">
          <h4 className="section-title">
            <FiLayers className="section-icon" />
            Batch Settings
          </h4>
          <div className="batch-size-container">
            <label htmlFor="batchSize">Batch Size:</label>
            <input
              id="batchSize"
              type="number"
              value={batchSize}
              onChange={(e) => setBatchSize(parseInt(e.target.value))}
              min="1"
              max="1000"
            />
          </div>
        </div>
        
        <div className="card-section">
          <h4 className="section-title">
            <FiUsers className="section-icon" />
            Sender Accounts
          </h4>
          {senderAccounts.map((account, index) => (
            <div key={index} className="sender-account-row">
              <div className="sender-account-field">
                <label>Sender Email:</label>
                <input
                  type="email"
                  placeholder="sender@company.com"
                  value={account.email}
                  onChange={(e) => updateSenderAccount(index, 'email', e.target.value)}
                  className="sender-account-input"
                />
              </div>
              <div className="sender-account-field">
                <label>App Password:</label>
                <input
                  type="password"
                  placeholder="App Password"
                  value={account.password}
                  onChange={(e) => updateSenderAccount(index, 'password', e.target.value)}
                  className="sender-account-input"
                />
              </div>
              <div className="sender-account-field">
                <label>Sender Name:</label>
                <input
                  type="text"
                  placeholder="e.g., John Smith"
                  value={account.sender_name}
                  onChange={(e) => updateSenderAccount(index, 'sender_name', e.target.value)}
                  className="sender-account-input"
                />
                <small style={{color: '#64748b', fontSize: '0.75rem'}}>
                  Will show as "Sender Name &lt;email&gt;"
                </small>
              </div>
              <button 
                onClick={() => removeSenderAccount(index)}
                className="remove-account-btn"
                disabled={senderAccounts.length <= 1}
                title="Remove account"
              >
                <FiX />
              </button>
            </div>
          ))}
          
          <button 
            onClick={addSenderAccount}
            className="add-account-btn"
          >
            <FiPlus /> Add Account
          </button>
        </div>

        <div className="card-section">
          <button 
            className="btn btn-send" 
            onClick={handleUpload} 
            disabled={
              !file || 
              sending || 
              loading.upload || 
              (useTemplates ? (!templateFile || loadedTemplates.length === 0) : (!emailContent.subject || !emailContent.body || !emailContent.sender_name))
            }
          >
            {loading.upload ? (
              <>
                <div className="loading-spinner"></div>
                Starting...
              </>
            ) : sending ? (
              <>
                <FiRefreshCw className="spinning" /> Sending...
              </>
            ) : (
              <>
                <FiSend /> Send Emails
              </>
            )}
          </button>
        </div>
      </div>

      {/* Progress Card */}
      {(sending || progress.status !== "idle") && (
        <div className="card progress-card">
          <div className="card-header">
            <div className="card-icon-wrapper">
              <FiBarChart2 className="card-main-icon" />
            </div>
            <h3>Email Sending Progress</h3>
          </div>
          
          <div className="progress-stats">
            <div className="progress-stat">
              <span className="progress-stat-value">{progress.sent}</span>
              <span className="progress-stat-label">Sent</span>
            </div>
            <div className="progress-stat">
              <span className="progress-stat-value">{progress.total}</span>
              <span className="progress-stat-label">Total</span>
            </div>
            <div className="progress-stat">
              <span className="progress-stat-value">{Math.round(progressPercentage)}%</span>
              <span className="progress-stat-label">Complete</span>
            </div>
          </div>

          <div className="progress-bar-container">
            <div 
              className="progress-bar" 
              style={{ width: `${progressPercentage}%` }}
            ></div>
          </div>

          <div className={`status-badge status-${progress.status.split(' ')[0]}`}>
            {progress.status === "running" && <FiRefreshCw className="spinning" />}
            {progress.status === "completed" && <FiCheck />}
            {progress.status.startsWith("error") && <FiX />}
            {progress.status === "idle" && "⸻"}
            Status: {progress.status.charAt(0).toUpperCase() + progress.status.slice(1)}
          </div>
        </div>
      )}
    </>
  );
}

export default AutoEmailTab;
