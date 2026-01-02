import mysql.connector
from mysql.connector import Error
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv

class Database:
    def __init__(self):
        load_dotenv()

        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")

        self.create_database_and_tables()

    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                ssl_ca="/etc/ssl/certs/rds-ca.pem",   # <- always exists in container
                ssl_verify_cert=True
            )
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def create_database_and_tables(self):
        connection = None
        cursor = None
        try:
            # First connect without database to create it
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = connection.cursor()
            
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create user_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create user_settings table to store individual user data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT UNIQUE,
                    zoho_client_id VARCHAR(255),
                    zoho_client_secret VARCHAR(255),
                    zoho_redirect_uri VARCHAR(255),
                    zoho_access_token TEXT,
                    zoho_refresh_token TEXT,
                    email_content TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            # Add this to the create_database_and_tables method after user_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    reset_token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            connection.commit()
            print("Database and tables created successfully!")
            
        except Error as e:
            print(f"Error creating database: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username, email, password):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                password_hash = self.hash_password(password)
                
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
                connection.commit()
                return cursor.lastrowid
            except Error as e:
                print(f"Error creating user: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None
    
    def verify_user(self, username, password):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                password_hash = self.hash_password(password)
                
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s AND password_hash = %s AND is_active = TRUE",
                    (username, password_hash)
                )
                user = cursor.fetchone()
                return user
            except Error as e:
                print(f"Error verifying user: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None
    
    def create_session(self, user_id, session_token, expires_at):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO user_sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
                    (user_id, session_token, expires_at)
                )
                connection.commit()
                return True
            except Error as e:
                print(f"Error creating session: {e}")
                return False
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return False
    
    def get_user_by_session(self, session_token):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT u.* FROM users u 
                    JOIN user_sessions us ON u.id = us.user_id 
                    WHERE us.session_token = %s AND us.expires_at > NOW()
                """, (session_token,))
                user = cursor.fetchone()
                return user
            except Error as e:
                print(f"Error getting user by session: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None
    
    def delete_session(self, session_token):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM user_sessions WHERE session_token = %s", (session_token,))
                connection.commit()
                return True
            except Error as e:
                print(f"Error deleting session: {e}")
                return False
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return False
    
    def create_password_reset_token(self, user_id):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # Delete any existing tokens for this user
                cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))
                
                # Create new token
                reset_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=1)  # 1 hour expiry
                
                cursor.execute(
                    "INSERT INTO password_reset_tokens (user_id, reset_token, expires_at) VALUES (%s, %s, %s)",
                    (user_id, reset_token, expires_at)
                )
                connection.commit()
                return reset_token
            except Error as e:
                print(f"Error creating reset token: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None

    def get_user_by_reset_token(self, reset_token):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT u.* FROM users u 
                    JOIN password_reset_tokens prt ON u.id = prt.user_id 
                    WHERE prt.reset_token = %s AND prt.expires_at > NOW() AND prt.used = FALSE
                """, (reset_token,))
                user = cursor.fetchone()
                return user
            except Error as e:
                print(f"Error getting user by reset token: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None

    def mark_reset_token_used(self, reset_token):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "UPDATE password_reset_tokens SET used = TRUE WHERE reset_token = %s",
                    (reset_token,)
                )
                connection.commit()
                return True
            except Error as e:
                print(f"Error marking token as used: {e}")
                return False
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return False

    def get_user_by_email(self, email):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s AND is_active = TRUE",
                    (email,)
                )
                user = cursor.fetchone()
                return user
            except Error as e:
                print(f"Error getting user by email: {e}")
                return None
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return None

    def update_user_password(self, user_id, new_password):
        connection = self.get_connection()
        if connection:
            try:
                cursor = connection.cursor()
                password_hash = self.hash_password(new_password)
                
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, user_id)
                )
                connection.commit()
                return True
            except Error as e:
                print(f"Error updating password: {e}")
                return False
            finally:
                if cursor:
                    cursor.close()
                if connection.is_connected():
                    connection.close()
        return False

# Global database instance
db = Database()
