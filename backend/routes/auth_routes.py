from flask import Blueprint, request, jsonify, make_response
import secrets
from datetime import datetime, timedelta
from database import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    
    if not all([username, email, password]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    user_id = db.create_user(username, email, password)
    if user_id:
        return jsonify({"message": "User created successfully", "user_id": user_id}), 201
    else:
        return jsonify({"error": "Username or email already exists"}), 400

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not all([username, password]):
        return jsonify({"error": "Missing username or password"}), 400
    
    user = db.verify_user(username, password)
    if user:
        # Create session
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)  # 7-day session
        
        if db.create_session(user["id"], session_token, expires_at):
            response = make_response(jsonify({
                "message": "Login successful",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"]
                }
            }))
            response.set_cookie(
                "session_token",
                session_token,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="Lax",
                max_age=7*24*60*60  # 7 days
            )
            return response
    
    return jsonify({"error": "Invalid username or password"}), 401

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session_token = request.cookies.get("session_token")
    if session_token:
        db.delete_session(session_token)
    
    response = make_response(jsonify({"message": "Logout successful"}))
    response.set_cookie("session_token", "", expires=0)
    return response

# auth_routes.py - Update the check_auth endpoint
@auth_bp.route("/check-auth", methods=["GET"])
def check_auth():
    session_token = request.cookies.get("session_token")
    if session_token:
        user = db.get_user_by_session(session_token)
        if user:
            return jsonify({
                "authenticated": True,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"]
                }
            })
    
    # Return 200 with authenticated: false instead of 401
    return jsonify({"authenticated": False})

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    user = db.get_user_by_email(email)
    if user:
        # In a real application, you would send an email here
        # For this example, we'll just return the reset token
        reset_token = db.create_password_reset_token(user["id"])
        if reset_token:
            # In production, send email with reset link
            reset_link = f"http://13.232.64.40:3000/reset-password?token={reset_token}"
            print(f"Password reset link for {email}: {reset_link}")  # Remove in production
            
            return jsonify({
                "message": "If an account with that email exists, a reset link has been sent",
                "reset_token": reset_token  # Remove this in production - only for demo
            })
    
    # Always return success to prevent email enumeration
    return jsonify({
        "message": "If an account with that email exists, a reset link has been sent"
    })

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("new_password")
    
    if not all([token, new_password]):
        return jsonify({"error": "Token and new password are required"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    user = db.get_user_by_reset_token(token)
    if not user:
        return jsonify({"error": "Invalid or expired reset token"}), 400
    
    if db.update_user_password(user["id"], new_password):
        db.mark_reset_token_used(token)
        return jsonify({"message": "Password reset successfully"})
    else:
        return jsonify({"error": "Failed to reset password"}), 500

@auth_bp.route("/validate-reset-token", methods=["POST"])
def validate_reset_token():
    data = request.json
    token = data.get("token")
    
    if not token:
        return jsonify({"error": "Token is required"}), 400
    
    user = db.get_user_by_reset_token(token)
    if user:
        return jsonify({"valid": True, "username": user["username"]})
    else:
        return jsonify({"valid": False}), 400
