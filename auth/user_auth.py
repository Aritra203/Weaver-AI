"""
User authentication and session management for Weaver AI
"""

import hashlib
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st

class UserManager:
    """Manages user authentication and user-specific data"""
    
    def __init__(self):
        """Initialize the user manager"""
        self.db_path = "data/users/users.db"
        self.ensure_users_db()
    
    def ensure_users_db(self):
        """Ensure the users database exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create user sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return {"success": False, "message": "Username or email already exists"}
            
            # Create user
            password_hash = self.hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            """, (username, email, password_hash))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Create user-specific directories
            self.create_user_directories(username)
            
            return {"success": True, "message": "User registered successfully", "user_id": user_id}
            
        except Exception as e:
            return {"success": False, "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login a user and create session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user
            cursor.execute("SELECT id, password_hash FROM users WHERE username = ? AND is_active = TRUE", (username,))
            user = cursor.fetchone()
            
            if not user or not self.verify_password(password, user[1]):
                return {"success": False, "message": "Invalid username or password"}
            
            user_id = user[0]
            
            # Update last login
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            
            # Create session token
            session_token = hashlib.sha256(f"{user_id}{datetime.now()}".encode()).hexdigest()
            expires_at = datetime.now() + timedelta(days=7)  # 7 days expiry
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, session_token, expires_at))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True, 
                "message": "Login successful",
                "user_id": user_id,
                "username": username,
                "session_token": session_token
            }
            
        except Exception as e:
            return {"success": False, "message": f"Login failed: {str(e)}"}
    
    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user info"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.user_id, u.username, u.email, s.expires_at
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.is_active = TRUE AND s.expires_at > CURRENT_TIMESTAMP
            """, (session_token,))
            
            session = cursor.fetchone()
            conn.close()
            
            if session:
                return {
                    "user_id": session[0],
                    "username": session[1],
                    "email": session[2],
                    "expires_at": session[3]
                }
            return None
            
        except Exception as e:
            return None
    
    def logout_user(self, session_token: str) -> bool:
        """Logout a user by invalidating session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE user_sessions SET is_active = FALSE WHERE session_token = ?", (session_token,))
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            return False
    
    def create_user_directories(self, username: str):
        """Create user-specific directories"""
        user_data_path = f"data/users/{username}"
        
        directories = [
            f"{user_data_path}/raw",
            f"{user_data_path}/processed", 
            f"{user_data_path}/vector_db",
            f"{user_data_path}/uploads"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_user_data_path(self, username: str) -> str:
        """Get the data path for a specific user"""
        return f"data/users/{username}"
    
    def clear_user_knowledge_base(self, username: str) -> bool:
        """Clear a user's knowledge base"""
        try:
            import shutil
            user_data_path = self.get_user_data_path(username)
            
            paths_to_clear = [
                f"{user_data_path}/raw",
                f"{user_data_path}/processed",
                f"{user_data_path}/vector_db"
            ]
            
            for path in paths_to_clear:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    os.makedirs(path, exist_ok=True)
            
            return True
            
        except Exception as e:
            return False


class AuthUI:
    """Authentication UI components"""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    def render_auth_forms(self) -> Optional[Dict[str, Any]]:
        """Render login/register forms and handle authentication"""
        
        # Check if user is already logged in
        if "user_session" in st.session_state and st.session_state.user_session:
            user_info = self.user_manager.verify_session(st.session_state.user_session["session_token"])
            if user_info:
                return user_info
            else:
                # Session expired, clear it
                st.session_state.user_session = None
        
        st.title("🧠 Weaver AI - Sign In")
        st.markdown("*Your intelligent project knowledge assistant*")
        
        # Auth form tabs
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
        
        with tab1:
            self.render_login_form()
        
        with tab2:
            self.render_register_form()
        
        return None
    
    def render_login_form(self):
        """Render the login form"""
        st.subheader("Sign In to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Please fill in all fields")
                    return
                
                result = self.user_manager.login_user(username, password)
                
                if result["success"]:
                    st.session_state.user_session = {
                        "user_id": result["user_id"],
                        "username": result["username"],
                        "session_token": result["session_token"]
                    }
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error(result["message"])
    
    def render_register_form(self):
        """Render the registration form"""
        st.subheader("Create New Account")
        
        with st.form("register_form"):
            username = st.text_input("Username", placeholder="Choose a username")
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            submitted = st.form_submit_button("Sign Up", use_container_width=True)
            
            if submitted:
                if not all([username, email, password, password_confirm]):
                    st.error("Please fill in all fields")
                    return
                
                if password != password_confirm:
                    st.error("Passwords do not match")
                    return
                
                if len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                    return
                
                if len(username) < 3:
                    st.error("Username must be at least 3 characters long")
                    return
                
                if "@" not in email:
                    st.error("Please enter a valid email address")
                    return
                
                result = self.user_manager.register_user(username, email, password)
                
                if result["success"]:
                    st.success("Account created successfully! Please sign in.")
                else:
                    st.error(result["message"])
    
    def render_user_info(self, user_info: Dict[str, Any]):
        """Render user info in sidebar"""
        with st.sidebar:
            st.markdown("---")
            st.subheader("👤 Account")
            st.write(f"**User**: {user_info['username']}")
            st.write(f"**Email**: {user_info['email']}")
            
            if st.button("🚪 Sign Out", type="secondary"):
                if "user_session" in st.session_state:
                    self.user_manager.logout_user(st.session_state.user_session["session_token"])
                    st.session_state.user_session = None
                    st.rerun()
