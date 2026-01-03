// LoginPage.js
import React, { useState } from "react";
import { FiMail, FiLock, FiUser, FiLogIn, FiUserPlus, FiEye, FiEyeOff, FiSend, FiArrowLeft } from "react-icons/fi";
import "./LoginPage.css";

function LoginPage({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: ""
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [cardTilt, setCardTilt] = useState({ x: 0, y: 0 });
  
  // Forgot Password states
  const [forgotPassword, setForgotPassword] = useState(false);
  const [resetStep, setResetStep] = useState(1); // 1: enter email, 2: enter new password
  const [resetToken, setResetToken] = useState("");
  const [resetEmail, setResetEmail] = useState("");

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const endpoint = isLogin ? "auth/login" : "auth/register";
      const response = await fetch(`https://65.1.129.37/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
        credentials: "include"
      });

      const data = await response.json();

      if (response.ok) {
        if (isLogin) {
          onLogin(data.user);
          setMessage({ type: "success", text: "Login successful!" });
        } else {
          setMessage({ type: "success", text: "Registration successful! Please login." });
          setIsLogin(true);
          setFormData({ username: "", email: "", password: "" });
        }
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const response = await fetch("https://65.1.129.37/auth/forgot-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: resetEmail }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ 
          type: "success", 
          text: data.message + " Check the console for the reset link (demo only)." 
        });
        // For demo purposes, we'll automatically proceed to next step
        if (data.reset_token) {
          setResetToken(data.reset_token);
          setResetStep(2);
        }
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const response = await fetch("https://65.1.129.37/auth/reset-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: resetToken,
          new_password: formData.password
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: "success", text: data.message });
        setTimeout(() => {
          setForgotPassword(false);
          setResetStep(1);
          setResetEmail("");
          setResetToken("");
          setFormData({ username: "", email: "", password: "" });
          setIsLogin(true);
        }, 2000);
      } else {
        setMessage({ type: "error", text: data.error });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Network error. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLogin = () => {
    setForgotPassword(false);
    setResetStep(1);
    setResetEmail("");
    setResetToken("");
    setFormData({ username: "", email: "", password: "" });
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleMouseMove = (e) => {
    const card = e.currentTarget;
    const cardRect = card.getBoundingClientRect();
    const cardWidth = cardRect.width;
    const cardHeight = cardRect.height;
    const centerX = cardRect.left + cardWidth / 2;
    const centerY = cardRect.top + cardHeight / 2;
    const mouseX = e.clientX - centerX;
    const mouseY = e.clientY - centerY;
    
    const rotateY = (mouseX / cardWidth) * 10;
    const rotateX = -(mouseY / cardHeight) * 10;
    
    setCardTilt({ x: rotateX, y: rotateY });
  };

  const handleMouseLeave = () => {
    setCardTilt({ x: 0, y: 0 });
  };

  return (
    <div className="login-container">
      {/* Premium Background Elements */}
      <div className="premium-bg">
        <div className="floating-card card-1"></div>
        <div className="floating-card card-2"></div>
        <div className="floating-card card-3"></div>
        <div className="geometric-grid"></div>
        <div className="particle particle-1"></div>
        <div className="particle particle-2"></div>
        <div className="particle particle-3"></div>
      </div>
      
      <div 
        className="login-card"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          transform: `perspective(1000px) rotateX(${cardTilt.x}deg) rotateY(${cardTilt.y}deg)`
        }}
      >
        {/* Corner Accents */}
        <div className="corner-accent corner-tl"></div>
        <div className="corner-accent corner-br"></div>

        {!forgotPassword ? (
          <div className="login-header">
            <div className="login-icon">
              <FiSend />
            </div>
            <h2>Cube AI Email Sender</h2>
            <p>{isLogin ? "Sign in to your account" : "Create a new account"}</p>
          </div>
        ) : null}

        {message.text && (
          <div className={`message ${message.type}`}>
            {message.text}
          </div>
        )}

        {forgotPassword ? (
          <form className="login-form" onSubmit={resetStep === 1 ? handleForgotPassword : handleResetPassword}>
            <div className="login-header">
              <div className="login-icon">
                <FiLock />
              </div>
              <h2>Reset Password</h2>
              <p>{resetStep === 1 ? "Enter your email address" : "Enter your new password"}</p>
            </div>

            {resetStep === 1 && (
              <div className="form-group floating-label">
                <FiMail className="input-icon" />
                <input
                  type="email"
                  name="resetEmail"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  required
                  placeholder=" "
                />
                <label>Email Address</label>
              </div>
            )}

            {resetStep === 2 && (
              <div className="form-group floating-label">
                <FiLock className="input-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                  placeholder=" "
                />
                <label>New Password</label>
                <button
                  type="button"
                  className="password-toggle"
                  onClick={togglePasswordVisibility}
                  tabIndex="-1"
                >
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            )}

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? (
                <>
                  <div className="loading-spinner"></div>
                  {resetStep === 1 ? "Sending..." : "Resetting..."}
                </>
              ) : (
                <>
                  {resetStep === 1 ? <FiSend /> : <FiLock />}
                  {resetStep === 1 ? "Send Reset Link" : "Reset Password"}
                </>
              )}
            </button>

            <div className="toggle-mode">
              <p>
                Remember your password?
                <button 
                  type="button" 
                  className="toggle-btn" 
                  onClick={handleBackToLogin}
                >
                  Back to Login
                </button>
              </p>
            </div>
          </form>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            {!isLogin && (
              <div className="form-group floating-label">
                <FiMail className="input-icon" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  placeholder=" "
                />
                <label>Email Address</label>
              </div>
            )}

            <div className="form-group floating-label">
              <FiUser className="input-icon" />
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                required
                placeholder=" "
              />
              <label>Username</label>
            </div>

            <div className="form-group floating-label">
              <FiLock className="input-icon" />
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                placeholder=" "
              />
              <label>Password</label>
              <button
                type="button"
                className="password-toggle"
                onClick={togglePasswordVisibility}
                tabIndex="-1"
              >
                {showPassword ? <FiEyeOff /> : <FiEye />}
              </button>
            </div>

            {isLogin && (
              <button 
                type="button" 
                className="forgot-password-link" 
                onClick={() => setForgotPassword(true)}
              >
                Forgot your password?
              </button>
            )}

            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? (
                <>
                  <div className="loading-spinner"></div>
                  {isLogin ? "Signing in..." : "Creating account..."}
                </>
              ) : (
                <>
                  {isLogin ? <FiLogIn /> : <FiUserPlus />}
                  {isLogin ? "Sign In" : "Create Account"}
                </>
              )}
            </button>
          </form>
        )}

        {!forgotPassword && (
          <div className="toggle-mode">
            <p>
              {isLogin ? "Don't have an account?" : "Already have an account?"}
              <button
                type="button"
                className="toggle-btn"
                onClick={() => setIsLogin(!isLogin)}
              >
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default LoginPage;
