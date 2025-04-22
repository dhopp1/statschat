from datetime import datetime, timedelta
import extra_streamlit_components as stx
import streamlit as st
import hmac


def get_cookie_manager():
    return stx.CookieManager()


def check_password():
    """Check if a user entered the password correctly"""
    st.session_state["cookie_manager"] = get_cookie_manager()

    if st.session_state["cookie_manager"].get(cookie="logged_in_statschat") == True:
        st.session_state["password_correct"] = True

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            condition = hmac.compare_digest(
                st.session_state["password"],
                st.secrets["password"],
            )
        except:
            condition = False

        if condition:
            # cookie
            expires_at = datetime.now() + timedelta(days=30)
            st.session_state["cookie_manager"].set(
                cookie="logged_in_statschat",
                val="true",
                expires_at=expires_at,
                key="logged_in_statschat",
            )

            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Password incorrect")

    return False
