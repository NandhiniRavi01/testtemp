import React, { useState, useEffect } from "react";
import WebScrapingTab from "./components/WebScrapingTab";
import AutoEmailTab from "./components/AutoEmailTab";
import ZohoCRMTab from "./components/ZohoCRMTab";
import EmailValidator from "./components/EmailValidator"; // Add this import
import Homepage from "./components/Homepage";
import LoginPage from "./components/LoginPage";
import { 
  FiMail, 
  FiUser, 
  FiLogOut, 
  FiSearch, 
  FiChevronLeft, 
  FiChevronRight,
  FiCpu,
  FiCheckCircle // Add this icon for email validator
} from "react-icons/fi";
import "./App.css";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState("webscraping"); // Default to first tab
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch("https://65.1.129.37:5000/auth/check-auth", {
        credentials: "include",
      });
      const data = await response.json();

      if (data.authenticated) {
        setIsAuthenticated(true);
        setCurrentUser(data.user);
      }
    } catch (error) {
      console.error("Error checking auth status:", error);
    } finally {
      setCheckingAuth(false);
    }
  };

  const handleLogin = (user) => {
    setIsAuthenticated(true);
    setCurrentUser(user);
    setShowLogin(false);
  };

  const handleShowLogin = () => {
    setShowLogin(true);
  };

  const handleShowHomepage = () => {
    setShowLogin(false);
  };

  const handleLogout = async () => {
    try {
      await fetch("https://65.1.129.37:5000/auth/logout", {
        method: "POST",
        credentials: "include",
      });

      localStorage.removeItem("zohoCredentials");
      localStorage.removeItem("zohoStatus");
      localStorage.removeItem("connectionStatus");
      localStorage.removeItem("emailContent");
    } catch (error) {
      console.error("Error logging out:", error);
    } finally {
      setIsAuthenticated(false);
      setCurrentUser(null);
      setShowLogin(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className="loading-container">
        <div className="loading-spinner-large"></div>
        <p className="loading-text">Checking authentication...</p>
      </div>
    );
  }

  // Show public homepage when not authenticated and not on login page
  if (!isAuthenticated && !showLogin) {
    return (
      <div className="public-homepage">
        <Homepage onLoginClick={handleShowLogin} />
      </div>
    );
  }

  // Show login page when login button is clicked
  if (!isAuthenticated && showLogin) {
    return <LoginPage onLogin={handleLogin} onBackToHome={handleShowHomepage} />;
  }

  // Only authenticated users see the dashboard
  const navItems = [
    { id: "webscraping", label: "Web Scraping", icon: <FiSearch /> },
    { id: "emailValidator", label: "Email Validator", icon: <FiCheckCircle /> }, // Add this tab
    { id: "autoEmail", label: "Auto Email", icon: <FiMail /> },
    { id: "zohoCRM", label: "Zoho CRM", icon: <FiCpu /> },
  ];

  const renderActiveTab = () => {
    switch (activeTab) {
      case "webscraping":
        return <WebScrapingTab />;
      case "emailValidator": // Add this case
        return <EmailValidator />;
      case "autoEmail":
        return <AutoEmailTab />;
      case "zohoCRM":
        return <ZohoCRMTab />;
      default:
        return <WebScrapingTab />;
    }
  };

  return (
    <div className="app-container">
      {/* Dashboard sidebar and content */}
      <div className={`sidebar ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            {!sidebarCollapsed && (
              <>
                <div className="logo-icon">
                  <FiCpu />
                </div>
                <div className="logo-text">
                  <h2>CubeAI</h2>
                  <span>Solutions</span>
                </div>
              </>
            )}
            <button 
              className="sidebar-toggle"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            >
              {sidebarCollapsed ? <FiChevronRight /> : <FiChevronLeft />}
            </button>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`sidebar-item ${activeTab === item.id ? "active" : ""}`}
              onClick={() => setActiveTab(item.id)}
              title={sidebarCollapsed ? item.label : ''}
            >
              <span className="sidebar-icon">{item.icon}</span>
              {!sidebarCollapsed && <span className="sidebar-label">{item.label}</span>}
            </button>
          ))}
        </nav>
        
        {!sidebarCollapsed && (
          <div className="sidebar-footer">
            <div className="user-profile">
              <div className="user-avatar">
                <FiUser />
              </div>
              <div className="user-info">
                <span className="user-name">{currentUser?.username || "Admin User"}</span>
                <span className="user-role">Administrator</span>
              </div>
            </div>
            <button onClick={handleLogout} className="logout-btn">
              <FiLogOut /> <span>Logout</span>
            </button>
          </div>
        )}

        {sidebarCollapsed && (
          <div className="sidebar-footer-collapsed">
            <button onClick={handleLogout} className="logout-btn-icon" title="Logout">
              <FiLogOut />
            </button>
          </div>
        )}
      </div>

      <div className={`main-content ${sidebarCollapsed ? 'main-content-expanded' : ''}`}>
        <div className="page-header">
          <div className="header-content">
            <div className="header-main">
              <h1 className="page-title">
                {activeTab === 'webscraping' && 'LinkedIn Lead Generator'}
                {activeTab === 'emailValidator' && 'Email Validator'} {/* Add this title */}
                {activeTab === 'autoEmail' && 'Automated Email Campaign'}
                {activeTab === 'zohoCRM' && 'Zoho CRM Integration'}
              </h1>
              <p className="page-subtitle">
                {activeTab === 'webscraping' && 'Find professional contacts with verified email addresses'}
                {activeTab === 'emailValidator' && 'Generate and validate email addresses from names and companies'} {/* Add this subtitle */}
                {activeTab === 'autoEmail' && 'Send personalized bulk emails with AI-generated content'}
                {activeTab === 'zohoCRM' && 'Manage leads and automate responses via Zoho CRM'}
              </p>
            </div>
            {sidebarCollapsed && (
              <div className="header-user">
                <div className="user-avatar-small">
                  <FiUser />
                </div>
                <span>{currentUser?.username || "Admin"}</span>
              </div>
            )}
          </div>
        </div>

        <div className="content-area">
          {renderActiveTab()}
        </div>
      </div>
    </div>
  );
}

export default App;
