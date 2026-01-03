import React, { useState, useEffect } from "react";
import { 
  FiSettings, FiDatabase, FiExternalLink, FiRefreshCw,
  FiSave, FiInbox, FiMessageSquare, FiEdit, FiTrash2,
  FiSend, FiDownload, FiCheck, FiX, FiUsers, FiMail,
  FiFileText, FiBarChart
} from "react-icons/fi";
import "./ZohoCRMTab.css";

function ZohoCRMTab() {
  // Load initial state from localStorage or use defaults
  const [zohoCredentials, setZohoCredentials] = useState(() => {
    const saved = localStorage.getItem('zohoCredentials');
    return saved ? JSON.parse(saved) : {
      clientId: "",
      clientSecret: "",
      redirectUri: window.location.origin + "/zoho-callback"
    };
  });

  const [zohoStatus, setZohoStatus] = useState(() => {
    const saved = localStorage.getItem('zohoStatus');
    return saved ? JSON.parse(saved) : { connected: false, message: "Not connected to Zoho CRM" };
  });

  const [connectionStatus, setConnectionStatus] = useState(() => {
    return localStorage.getItem('connectionStatus') || "disconnected";
  });

  const [selectedSender, setSelectedSender] = useState("");
  const [selectedSenderPassword, setSelectedSenderPassword] = useState("");
  const [replies, setReplies] = useState([]);
  const [checkingReplies, setCheckingReplies] = useState(false);
  const [generatedReply, setGeneratedReply] = useState("");
  const [showReplyModal, setShowReplyModal] = useState(false);
  const [selectedReply, setSelectedReply] = useState(null);
  const [sendingReply, setSendingReply] = useState(false);
  const [generatingReply, setGeneratingReply] = useState(false);
  const [allGeneratedReplies, setAllGeneratedReplies] = useState({});
  const [editingReplyId, setEditingReplyId] = useState(null);
  const [sendingAll, setSendingAll] = useState(false);
  const [sentReplies, setSentReplies] = useState([]);
  const [debugInfo, setDebugInfo] = useState("");
  const [availableFields, setAvailableFields] = useState([]);

  // Save to localStorage whenever state changes
  useEffect(() => {
    localStorage.setItem('zohoCredentials', JSON.stringify(zohoCredentials));
  }, [zohoCredentials]);

  useEffect(() => {
    localStorage.setItem('zohoStatus', JSON.stringify(zohoStatus));
  }, [zohoStatus]);

  useEffect(() => {
    localStorage.setItem('connectionStatus', connectionStatus);
  }, [connectionStatus]);

  // Save Zoho credentials
  const saveZohoCredentials = async () => {
    if (!zohoCredentials.clientId || !zohoCredentials.clientSecret || !zohoCredentials.redirectUri) {
      alert("Please fill in all Zoho CRM credentials!");
      return;
    }

    try {
      const res = await fetch("http://65.1.129.37:5000/save-zoho-credentials", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": "default_user"
        },
        body: JSON.stringify({
          client_id: zohoCredentials.clientId,
          client_secret: zohoCredentials.clientSecret,
          redirect_uri: zohoCredentials.redirectUri
        }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        alert("Zoho credentials saved successfully!");
      } else {
        alert("Error saving credentials: " + data.error);
      }
    } catch (err) {
      alert("Error saving credentials: " + err.message);
    }
  };

  // Get Zoho status
  const getZohoStatus = async () => {
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-status");
      const data = await res.json();
      
      if (res.ok) {
        setZohoStatus(data);
        setConnectionStatus(data.connected ? "connected" : "disconnected");
        
        if (data.connected) {
          getZohoFields();
        }
      } else {
        setConnectionStatus("error");
        setDebugInfo("Failed to get Zoho status: " + JSON.stringify(data));
      }
    } catch (err) {
      setConnectionStatus("error");
      setDebugInfo("Error getting Zoho status: " + err.message);
      console.error("Error getting Zoho status:", err);
    }
  };

  // Get Zoho fields
  const getZohoFields = async () => {
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-fields");
      const data = await res.json();
      
      if (res.ok) {
        setAvailableFields(data.fields || []);
        setDebugInfo("Available fields: " + JSON.stringify(data.fields, null, 2));
      } else {
        setDebugInfo("Failed to get field information: " + JSON.stringify(data));
      }
    } catch (err) {
      setDebugInfo("Error getting field information: " + err.message);
      console.error("Error getting field information:", err);
    }
  };

  // Connect to Zoho (open auth URL)
  const connectZoho = async () => {
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-auth");
      const data = await res.json();
      
      if (res.ok) {
        window.open(data.auth_url, "_blank");
        setTimeout(getZohoStatus, 3000);
      } else {
        alert("Error connecting to Zoho: " + data.error);
      }
    } catch (err) {
      alert("Error connecting to Zoho: " + err.message);
    }
  };

  // Helper to generate a single professional reply
  const generateSingleReply = async (reply) => {
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-generate-professional-reply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          original_email: reply.body
        }),
      });
      
      const data = await res.json();
      return res.ok ? data.reply : "Error generating professional reply";
    } catch (err) {
      return "Error generating professional reply: " + err.message;
    }
  };

  // Check replies (fetch from backend and auto-generate replies)
  const checkReplies = async () => {
    if (!selectedSender || !selectedSenderPassword) {
      alert("Please enter sender email and password");
      return;
    }

    setCheckingReplies(true);
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-check-replies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sender_email: selectedSender,
          sender_password: selectedSenderPassword
        }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setReplies(data.replies);
        
        const generatedReplies = {};
        for (const reply of data.replies) {
          const generated = await generateSingleReply(reply);
          generatedReplies[reply.id] = generated;
        }
        
        setAllGeneratedReplies(generatedReplies);
        alert(data.message);
      } else {
        alert("Error checking replies: " + data.error);
      }
    } catch (err) {
      alert("Error checking replies: " + err.message);
    } finally {
      setCheckingReplies(false);
    }
  };

  // Update a specific generated reply
  const updateGeneratedReply = (replyId, newContent) => {
    setAllGeneratedReplies(prev => ({
      ...prev,
      [replyId]: newContent
    }));
  };

  // Clear a specific generated reply
  const clearGeneratedReply = (replyId) => {
    setAllGeneratedReplies(prev => ({
      ...prev,
      [replyId]: ""
    }));
  };

  // Clear all replies from view
  const clearAllReplies = () => {
    if (window.confirm("Are you sure you want to clear all replies? This will remove them from the view but they will still be available in the Excel download.")) {
      setReplies([]);
      setAllGeneratedReplies({});
      setSentReplies([]);
    }
  };

  // Send all replies
  const sendAllReplies = async () => {
    if (!selectedSender || !selectedSenderPassword) {
      alert("Missing sender email or password");
      return;
    }

    setSendingAll(true);
    const results = [];
    const sentIds = [];
    
    for (const reply of replies) {
      if (allGeneratedReplies[reply.id] && allGeneratedReplies[reply.id].trim() !== "") {
        try {
          const res = await fetch("http://65.1.129.37:5000/zoho-send-reply", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              sender_email: selectedSender,
              sender_password: selectedSenderPassword,
              recipient_email: reply.from,
              subject: `Re: ${reply.subject}`,
              body: allGeneratedReplies[reply.id],
              email_id: reply.id,
              lead_data: {
                email: reply.from,
                first_name: reply.first_name || reply.from.split('@')[0],
                last_name: reply.last_name || "",
                company: reply.company || "From Email Reply",
                phone: reply.phone || ""
              }
            }),
          });
          
          const data = await res.json();
          const success = res.ok;
          
          results.push({
            email: reply.from,
            success,
            message: success ? "Sent successfully" : data.error
          });
          
          if (success) {
            sentIds.push(reply.id);
          }
        } catch (err) {
          results.push({
            email: reply.from,
            success: false,
            message: err.message
          });
        }
      }
    }
    
    setSendingAll(false);
    
    const successful = results.filter(r => r.success).length;
    alert(`Sent ${successful} out of ${results.length} replies.`);
    
    setSentReplies(prev => [...prev, ...sentIds]);
  };

  // Generate reply for a single item and show modal
  const generateReply = async (reply) => {
    setGeneratingReply(true);
    setSelectedReply(reply);
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-generate-professional-reply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          original_email: reply.body
        }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setGeneratedReply(data.reply);
        setShowReplyModal(true);
      } else {
        alert("Error generating professional reply: " + data.error);
      }
    } catch (err) {
      alert("Error generating professional reply: " + err.message);
    } finally {
      setGeneratingReply(false);
    }
  };

  // Send single reply from modal
  const sendReply = async () => {
    if (!selectedSender || !selectedSenderPassword || !selectedReply || !generatedReply) {
      alert("Missing information to send reply");
      return;
    }

    setSendingReply(true);
    try {
      const res = await fetch("http://65.1.129.37:5000/zoho-send-reply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sender_email: selectedSender,
          sender_password: selectedSenderPassword,
          recipient_email: selectedReply.from,
          subject: `Re: ${selectedReply.subject}`,
          body: generatedReply,
          email_id: selectedReply.id,
          lead_data: {
            email: selectedReply.from,
            first_name: selectedReply.from.split('@')[0],
            company: "From Email Reply"
          }
        }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        alert("Reply sent successfully!");
        setShowReplyModal(false);
        setGeneratedReply("");
        setSelectedReply(null);
        setSentReplies(prev => [...prev, selectedReply.id]);
      } else {
        alert("Error sending reply: " + data.error);
      }
    } catch (err) {
      alert("Error sending reply: " + err.message);
    } finally {
      setSendingReply(false);
    }
  };

  // Download replies as Excel
  const downloadReplies = async () => {
    try {
      const res = await fetch("http://65.1.129.37:5000/download-replies");
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `email_replies_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const errorData = await res.json();
        alert("Error downloading file: " + (errorData.error || "No data available"));
      }
    } catch (err) {
      alert("Error downloading file: " + err.message);
    }
  };

  // Clear all Zoho data
  const clearZohoData = () => {
    if (window.confirm("Clear all saved Zoho data? This will remove your credentials and connection status.")) {
      localStorage.removeItem('zohoCredentials');
      localStorage.removeItem('zohoStatus');
      localStorage.removeItem('connectionStatus');
      
      setZohoCredentials({
        clientId: "",
        clientSecret: "",
        redirectUri: "https://yourdomain.com/zoho-callback"
      });
      setZohoStatus({ connected: false, message: "Not connected to Zoho CRM" });
      setConnectionStatus("disconnected");
      
      alert("Zoho data cleared!");
    }
  };

  // Update credential function
  const updateCredential = (field, value) => {
    setZohoCredentials(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Poll Zoho status on mount
  useEffect(() => {
    getZohoStatus();
  }, []);

  // Render connection UI
  const renderZohoConnectionSection = () => (
    <div className="card zoho-card">
      <div className="card-header">
        <div className="card-icon-wrapper">
          <FiDatabase className="card-main-icon" />
        </div>
        <h3>Zoho CRM Connection</h3>
      </div>
      
      <div className={`connection-status connection-${connectionStatus}`}>
        <div className="status-indicator"></div>
        <div className="status-text">
          <strong>Status:</strong> 
          {connectionStatus === "connected" && "Connected to Zoho CRM"}
          {connectionStatus === "disconnected" && "Not connected to Zoho CRM"}
          {connectionStatus === "testing" && "Testing connection..."}
          {connectionStatus === "error" && "Connection error"}
        </div>
        {zohoStatus.message && (
          <div className="status-message">{zohoStatus.message}</div>
        )}
      </div>
      
      <div className="controls">
        <button 
          className="btn btn-connect" 
          onClick={connectZoho}
          disabled={connectionStatus === "connected" || !zohoCredentials.clientId}
        >
          <FiExternalLink /> 
          {connectionStatus === "connected" ? "Connected" : "Connect to Zoho CRM"}
        </button>
        
        <button 
          className="btn btn-refresh" 
          onClick={getZohoStatus}
        >
          <FiRefreshCw /> Refresh Status
        </button>
      </div>
    </div>
  );

  // Render setup UI
  const renderZohoSetupSection = () => (
    <div className="card zoho-card">
      <div className="card-header">
        <div className="card-icon-wrapper">
          <FiSettings className="card-main-icon" />
        </div>
        <h3>Zoho CRM Setup</h3>
        <button 
          onClick={clearZohoData}
          className="btn btn-clear"
          style={{ marginLeft: 'auto', fontSize: '0.8rem', padding: '5px 10px' }}
          title="Clear saved data"
        >
          <FiTrash2 /> Clear Data
        </button>
      </div>
      
      <div className="card-section">
        <h4 className="section-title">
          <FiSave className="section-icon" />
          Zoho Credentials
          <span style={{ 
            fontSize: '0.8rem', 
            color: '#10b981', 
            marginLeft: '10px',
            fontWeight: 'normal'
          }}>
            ✓ Auto-saved locally
          </span>
        </h4>
        
        <div className="content-field">
          <label>Client ID:</label>
          <input
            type="text"
            value={zohoCredentials.clientId}
            onChange={(e) => updateCredential('clientId', e.target.value)}
            className="content-input"
            placeholder="Enter your Zoho Client ID"
          />
        </div>
        
        <div className="content-field">
          <label>Client Secret:</label>
          <input
            type="password"
            value={zohoCredentials.clientSecret}
            onChange={(e) => updateCredential('clientSecret', e.target.value)}
            className="content-input"
            placeholder="Enter your Zoho Client Secret"
          />
        </div>
        
        <div className="content-field">
          <label>Redirect URI:</label>
          <input
            type="text"
            value={zohoCredentials.redirectUri}
            onChange={(e) => updateCredential('redirectUri', e.target.value)}
            className="content-input"
            placeholder="https://yourdomain.com/zoho-callback"
          />
          <small>This should match the redirect URI configured in your Zoho app (e.g., https://yourdomain.com/zoho-callback)</small>
        </div>
        
        <div className="button-group">
          <button 
            className="btn btn-primary" 
            onClick={saveZohoCredentials}
          >
            <FiSave /> Save to Server
          </button>
          
          <button 
            className="btn btn-secondary"
            onClick={() => {
              alert(`Client ID: ${zohoCredentials.clientId ? '✓ Saved' : '✗ Empty'}\nClient Secret: ${zohoCredentials.clientSecret ? '✓ Saved' : '✗ Empty'}\n\nData is automatically saved locally.`);
            }}
          >
            <FiCheck /> Check Saved Data
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="zoho-tab">
      {renderZohoSetupSection()}
      {renderZohoConnectionSection()}

      {/* Check Replies Card */}
      <div className="card zoho-card">
        <div className="card-header">
          <div className="card-icon-wrapper">
            <FiInbox className="card-main-icon" />
          </div>
          <h3>Check for Replies</h3>
        </div>
        
        <div className="card-section">
          <h4 className="section-title">
            <FiMail className="section-icon" />
            Email Configuration
          </h4>
          
          <div className="content-field">
            <label>Sender Email Address:</label>
            <input
              type="email"
              value={selectedSender}
              onChange={(e) => setSelectedSender(e.target.value)}
              className="content-input"
              placeholder="Enter sender email address"
            />
          </div>
          
          <div className="content-field">
            <label>Email App Password:</label>
            <input
              type="password"
              value={selectedSenderPassword}
              onChange={(e) => setSelectedSenderPassword(e.target.value)}
              className="content-input"
              placeholder="Enter email app password"
            />
            <small>Note: Use App Password if 2FA is enabled on your Gmail account</small>
          </div>
        </div>
        
        <div className="controls">
          <button 
            className="btn btn-primary" 
            onClick={checkReplies}
            disabled={checkingReplies || !selectedSender || !selectedSenderPassword}
          >
            {checkingReplies ? (
              <>
                <div className="loading-spinner"></div>
                Checking...
              </>
            ) : (
              <>
                <FiInbox /> Check for Replies
              </>
            )}
          </button>
        </div>
      </div>

      {/* Replies List & Actions */}
      {replies.length > 0 && (
        <>
          <div className="card zoho-card">
            <div className="card-header">
              <div className="card-icon-wrapper">
                <FiMessageSquare className="card-main-icon" />
              </div>
              <h3>Unread Replies Found ({replies.length})</h3>
            </div>
            
            {replies.map((reply, index) => (
              <div key={index} className="zoho-reply-item" style={{
                opacity: sentReplies.includes(reply.id) ? 0.7 : 1,
                borderLeft: sentReplies.includes(reply.id) ? '4px solid #10b981' : '1px solid #e2e8f0'
              }}>
                <div className="zoho-reply-header">
                  <div className="zoho-reply-from">{reply.from}</div>
                  <div className="zoho-reply-date">{reply.date}</div>
                </div>
                
                <div className="zoho-reply-subject">{reply.subject}</div>
                
                <div className="zoho-reply-body">
                  {reply.body}
                </div>
                
                <div className="content-field">
                  <h4 className="section-title">
                    <FiEdit className="section-icon" />
                    Professional AI Reply
                  </h4>
                  {editingReplyId === reply.id ? (
                    <>
                      <textarea
                        value={allGeneratedReplies[reply.id] || ""}
                        onChange={(e) => updateGeneratedReply(reply.id, e.target.value)}
                        rows={4}
                        className="content-textarea"
                        placeholder="Professional reply will be generated..."
                        disabled={sentReplies.includes(reply.id)}
                      />
                      <div className="button-group" style={{marginTop: '10px'}}>
                        <button 
                          className="btn btn-primary"
                          onClick={() => setEditingReplyId(null)}
                          disabled={sentReplies.includes(reply.id)}
                        >
                          <FiSave /> Save
                        </button>
                        <button 
                          className="btn btn-clear"
                          onClick={() => clearGeneratedReply(reply.id)}
                          disabled={sentReplies.includes(reply.id)}
                        >
                          <FiTrash2 /> Clear
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="content-display body-display">
                        {allGeneratedReplies[reply.id] || "No professional reply generated yet"}
                      </div>
                      <div className="button-group" style={{marginTop: '10px'}}>
                        <button 
                          className="btn btn-secondary"
                          onClick={() => setEditingReplyId(reply.id)}
                          disabled={sentReplies.includes(reply.id)}
                        >
                          <FiEdit /> Edit
                        </button>
                        <button 
                          className="btn btn-generate-reply"
                          onClick={() => generateSingleReply(reply).then(content => 
                            updateGeneratedReply(reply.id, content)
                          )}
                          disabled={sentReplies.includes(reply.id)}
                        >
                          <FiRefreshCw /> Regenerate
                        </button>
                        <button
                          className="btn btn-primary"
                          onClick={() => generateReply(reply)}
                          disabled={sentReplies.includes(reply.id)}
                        >
                          <FiSend /> Generate & Send
                        </button>
                      </div>
                    </>
                  )}
                </div>
                
                {sentReplies.includes(reply.id) && (
                  <div style={{
                    padding: '10px',
                    background: '#f0fdf4',
                    borderRadius: '8px',
                    marginTop: '10px',
                    color: '#166534',
                    fontWeight: '500'
                  }}>
                    <FiCheck /> Reply sent successfully
                  </div>
                )}
              </div>
            ))}
            
            <div className="controls" style={{marginTop: '20px'}}>
              <button 
                className="btn btn-send"
                onClick={sendAllReplies}
                disabled={sendingAll || Object.keys(allGeneratedReplies).length === 0}
              >
                {sendingAll ? (
                  <>
                    <div className="loading-spinner"></div>
                    Sending All...
                  </>
                ) : (
                  <>
                    <FiSend /> Send All Replies
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Export Replies Card */}
          <div className="card zoho-card">
            <div className="card-header">
              <div className="card-icon-wrapper">
                <FiDownload className="card-main-icon" />
              </div>
              <h3>Export Replies Data</h3>
            </div>
            
            <div className="controls">
              <button 
                className="btn btn-download"
                onClick={downloadReplies}
              >
                <FiDownload /> Download Excel File
              </button>
            </div>
          </div>

          {/* Clear Replies Card */}
          <div className="card zoho-card">
            <div className="card-header">
              <div className="card-icon-wrapper">
                <FiTrash2 className="card-main-icon" />
              </div>
              <h3>Clear Replies</h3>
            </div>
            
            <div className="card-section">
              <h4 className="section-title">
                <FiFileText className="section-icon" />
                Clear All Replies
              </h4>
              <p>Clear all replies from the view. This will not affect the Excel download file.</p>
            </div>
            
            <div className="controls">
              <button 
                className="btn btn-clear"
                onClick={clearAllReplies}
              >
                <FiTrash2 /> Clear All Replies
              </button>
            </div>
          </div>
        </>
      )}

      {/* Reply Confirmation Modal */}
      {showReplyModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 className="modal-title">Send Professional Reply</h3>
              <button 
                className="modal-close"
                onClick={() => setShowReplyModal(false)}
              >
                <FiX />
              </button>
            </div>
            
            <div className="modal-body">
              <p><strong>To:</strong> {selectedReply?.from}</p>
              <p><strong>Subject:</strong> Re: {selectedReply?.subject}</p>
              
              <div className="content-field">
                <label>Professional Reply:</label>
                <textarea
                  value={generatedReply}
                  onChange={(e) => setGeneratedReply(e.target.value)}
                  rows={6}
                  className="content-textarea"
                />
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn btn-secondary"
                onClick={() => setShowReplyModal(false)}
              >
                <FiX /> Cancel
              </button>
              
              <button 
                className="btn btn-primary"
                onClick={sendReply}
                disabled={sendingReply}
              >
                {sendingReply ? (
                  <>
                    <div className="loading-spinner"></div>
                    Sending...
                  </>
                ) : (
                  <>
                    <FiSend /> Send Reply
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ZohoCRMTab;
